import itertools
import json
import secrets
import unicodedata
from unittest import mock

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import Client, SimpleTestCase, TestCase, override_settings

from . import game_rules
from .authentication import hash_token
from .models import GameSession, Member, Record
from .views import SAVE_WINDOW_SECONDS, now_ms

# 실제 해시(PBKDF2)는 느리므로 테스트에서는 빠른 해시를 쓴다.
FAST_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']

NORMAL = [1, 9, 0, 0]   # 1 + 9 = 10 → 보통 문제 (합 10)
HARD = [6, 7, 8, 9]     # 0·같은 숫자·합이 10인 쌍이 없고 합이 20 이상 → 어려운 문제 (합 30)
LOW = [0, 1, 1, 2]      # 합이 10인 쌍은 없지만 합이 작음 → 보통 문제 (합 4)
REPEATED = [9, 9, 9, 8]  # 합이 크고 합이 10인 쌍도 없지만 같은 숫자가 있음 → 보통 문제 (합 35)


@override_settings(PASSWORD_HASHERS=FAST_HASHERS)
class ApiTestCase(TestCase):
    """JSON API 호출을 짧게 쓰기 위한 공통 도우미."""

    def setUp(self):
        cache.clear()   # 요청 횟수 제한 카운터 초기화
        self.client = Client(raise_request_exception=False)

    def call(self, method, path, body=None, token=None, raw=None, **extra):
        kwargs = dict(extra)
        if token is not None:
            kwargs['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        if raw is not None:
            kwargs.update(data=raw, content_type='application/json')
        elif body is not None:
            kwargs.update(data=json.dumps(body), content_type='application/json')
        return getattr(self.client, method)(path, **kwargs)

    def assertDetail(self, response, status, fragment=None):
        self.assertEqual(response.status_code, status, response.content.decode())
        self.assertEqual(response['Content-Type'], 'application/json')
        data = response.json()
        self.assertEqual(list(data.keys()), ['detail'])
        if fragment is not None:
            self.assertIn(fragment, data['detail'])
        return data['detail']

    def make_member(self, nickname, password='pw1234'):
        token = secrets.token_urlsafe(16)
        member = Member.objects.create(
            nickname=nickname,
            password_hash=make_password(password) if password else '',
            token_hash=hash_token(token),
            created_at=now_ms(),
        )
        return member, token

    def make_record(self, member, score, *, nickname=None, accuracy=100.0,
                    average=1.0, created_at=1, duration=60, game_mode='score',
                    correct=1, survival_time=None):
        return Record.objects.create(
            id=secrets.token_hex(8),
            member=member,
            nickname=nickname or member.nickname,
            duration=duration,
            game_mode=game_mode,
            correct=correct,
            wrong=0,
            accuracy=accuracy,
            score=score,
            average_response_time=average,
            survival_time=survival_time,
            created_at=created_at,
        )

    def make_survival_record(self, member, survival_time, **kwargs):
        return self.make_record(
            member, 50, duration=0, game_mode='survival', survival_time=survival_time, **kwargs
        )

    def ranking(self, game_mode='score'):
        response = self.call('get', f'/api/records?gameMode={game_mode}')
        self.assertEqual(response.status_code, 200)
        return response.json()

    def start_game(self, token, game_mode='score'):
        response = self.call('post', '/api/games', {'gameMode': game_mode}, token=token)
        self.assertEqual(response.status_code, 201, response.content.decode())
        return response.json()

    def set_questions(self, game_id, digit_rows):
        """채점 결과를 예측할 수 있도록 발급된 문제를 정해진 숫자로 바꾼다."""
        questions = [
            {'platePrefix': '12', 'hangul': '가', 'digits': list(digits)}
            for digits in digit_rows
        ]
        GameSession.objects.filter(id=game_id).update(questions=questions)

    def rewind(self, game_id, seconds):
        """게임을 seconds 초 전에 시작한 것으로 만든다."""
        GameSession.objects.filter(id=game_id).update(
            started_at=now_ms() - int(seconds * 1000)
        )

    def save(self, token, game_id, answers, **extra_body):
        body = {'gameId': game_id, 'answers': answers, **extra_body}
        return self.call('post', '/api/records', body, token=token)


class ErrorFormatTests(ApiTestCase):
    """모든 오류는 {"detail": "한글 문구"} JSON 이어야 한다."""

    def test_health(self):
        response = self.call('get', '/api/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    def test_unknown_path_is_json_404(self):
        self.assertDetail(self.call('get', '/api/unknown'), 404, '찾을 수 없습니다')

    def test_trailing_slash_is_json_404(self):
        self.assertDetail(self.call('get', '/api/records/'), 404)

    def test_wrong_method_is_korean_405(self):
        self.assertDetail(self.call('get', '/api/register'), 405, '허용되지 않는')

    def test_malformed_json_is_korean_400(self):
        self.assertDetail(
            self.call('post', '/api/register', raw='{bad json'), 400, '해석할 수 없습니다'
        )

    def test_non_object_body_is_korean_400(self):
        self.assertDetail(
            self.call('post', '/api/register', raw='[1, 2]'), 400, '요청 형식'
        )

    def test_missing_credentials_is_korean_401(self):
        self.assertDetail(self.call('get', '/api/me'), 401, '회원 인증이 필요합니다')
        self.assertDetail(
            self.call('post', '/api/records', {'gameId': 'x', 'answers': []}),
            401,
            '회원 인증이 필요합니다',
        )

    def test_invalid_token_is_401(self):
        self.assertDetail(
            self.call('get', '/api/me', token='not-a-real-token'), 401, '유효하지 않은'
        )

    def test_unhandled_exception_is_json_500(self):
        with mock.patch(
            'game_api.views.HealthView.get', side_effect=RuntimeError('boom')
        ), self.assertLogs('django.request', level='ERROR'):
            response = self.call('get', '/api/health')
        self.assertDetail(response, 500, '서버 오류')


class SchemaTests(TestCase):
    def test_nickname_unique_ignores_ascii_case(self):
        Member.objects.create(nickname='Tester', token_hash='a', created_at=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Member.objects.create(nickname='tester', token_hash='b', created_at=2)

    def test_nickname_lookup_ignores_ascii_case(self):
        Member.objects.create(nickname='Tester', token_hash='a', created_at=1)
        self.assertTrue(Member.objects.filter(nickname='TESTER').exists())


class RegisterTests(ApiTestCase):
    def register(self, nickname, password='pw1234'):
        return self.call(
            'post', '/api/register', {'nickname': nickname, 'password': password}
        )

    def test_register_and_me(self):
        response = self.register('민준')
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['nickname'], '민준')
        self.assertTrue(data['hasPassword'])

        me = self.call('get', '/api/me', token=data['token'])
        self.assertEqual(
            me.json(), {'id': data['id'], 'nickname': '민준', 'hasPassword': True}
        )

    def test_password_is_stored_hashed(self):
        self.register('민준', 'secret-pw')
        member = Member.objects.get(nickname='민준')
        self.assertNotIn('secret-pw', member.password_hash)
        self.assertTrue(member.password_hash)

    def test_duplicate_nickname_ignores_case_and_outer_spaces(self):
        self.assertEqual(self.register('Tester').status_code, 201)
        self.assertDetail(self.register('tester'), 409, '이미 사용 중인')
        self.assertDetail(self.register('  TESTER  '), 409)

    def test_decomposed_hangul_is_composed(self):
        decomposed = unicodedata.normalize('NFD', '민준')
        self.assertNotEqual(decomposed, '민준')
        self.assertEqual(self.register(decomposed).json()['nickname'], '민준')

    def test_allowed_nicknames(self):
        for nickname in ('ㅋㅋ_민준-1', 'a b', 'A', '가' * 16):
            with self.subTest(nickname=nickname):
                self.assertEqual(self.register(nickname).status_code, 201)

    def test_rejected_nicknames(self):
        cases = {
            'zero-width lookalike': 'Tester​',
            'newline': 'a\nb',
            'double space': 'a  b',
            'fullwidth letters': 'Ａｂｃ',
            'emoji': '민준😀',
            'symbols': '<b>x</b>',
            'empty': '',
            'spaces only': '   ',
            'too long': 'x' * 17,
        }
        for label, nickname in cases.items():
            with self.subTest(label):
                self.assertDetail(self.register(nickname), 400, '닉네임')
        self.assertEqual(Member.objects.count(), 0)

    def test_password_length(self):
        self.assertDetail(self.register('민준', 'abc'), 400, '비밀번호는 4~64자')
        self.assertDetail(self.register('민준', 'x' * 65), 400, '비밀번호는 4~64자')
        self.assertDetail(
            self.call('post', '/api/register', {'nickname': '민준'}), 400, '비밀번호'
        )
        self.assertEqual(Member.objects.count(), 0)


class LoginTests(ApiTestCase):
    def login(self, nickname, password, **extra):
        return self.call(
            'post', '/api/login', {'nickname': nickname, 'password': password}, **extra
        )

    def test_login_rotates_token(self):
        _, old_token = self.make_member('Tester')
        response = self.login('Tester', 'pw1234')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['passwordSet'])

        self.assertDetail(self.call('get', '/api/me', token=old_token), 401)
        self.assertEqual(self.call('get', '/api/me', token=data['token']).status_code, 200)

    def test_nickname_alone_is_not_enough(self):
        _, token = self.make_member('Tester')
        self.assertDetail(self.login('Tester', 'wrong-pw'), 401, '비밀번호가 올바르지')
        self.assertDetail(
            self.call('post', '/api/login', {'nickname': 'Tester'}), 400, '비밀번호'
        )
        # 실패한 로그인은 기존 로그인(토큰)을 끊지 못한다.
        self.assertEqual(self.call('get', '/api/me', token=token).status_code, 200)

    def test_unknown_nickname(self):
        self.assertDetail(self.login('nobody', 'pw1234'), 401, '등록되지 않은')

    def test_login_ignores_ascii_case(self):
        self.make_member('Tester')
        response = self.login('tESTER', 'pw1234')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['nickname'], 'Tester')

    def test_member_without_password_sets_it_on_first_login(self):
        member, _ = self.make_member('옛회원', password=None)

        self.assertDetail(self.login('옛회원', 'abc'), 400, '비밀번호는 4~64자')
        member.refresh_from_db()
        self.assertFalse(member.has_password)

        first = self.login('옛회원', 'new-password')
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()['passwordSet'])
        self.assertTrue(first.json()['hasPassword'])

        self.assertDetail(self.login('옛회원', 'other-password'), 401)
        again = self.login('옛회원', 'new-password')
        self.assertEqual(again.status_code, 200)
        self.assertFalse(again.json()['passwordSet'])

    def test_logout_invalidates_token(self):
        _, token = self.make_member('Tester')
        self.assertEqual(self.call('post', '/api/logout', token=token).status_code, 200)
        self.assertDetail(self.call('get', '/api/me', token=token), 401)
        # 이미 무효가 된 토큰으로 다시 로그아웃하면 401 (프론트는 이때도 로컬 상태를 지운다)
        self.assertDetail(self.call('post', '/api/logout', token=token), 401)


class WithdrawTests(ApiTestCase):
    def withdraw(self, token, password=None):
        body = {} if password is None else {'password': password}
        return self.call('delete', '/api/account', body, token=token)

    def test_requires_password(self):
        member, token = self.make_member('Tester')
        self.assertDetail(self.withdraw(token), 403, '비밀번호가 올바르지')
        self.assertDetail(self.withdraw(token, 'wrong-pw'), 403)
        self.assertTrue(Member.objects.filter(id=member.id).exists())
        # 실패해도 로그인은 유지된다.
        self.assertEqual(self.call('get', '/api/me', token=token).status_code, 200)

    def test_withdraw_keeps_records_and_marks_them(self):
        member, token = self.make_member('Tester')
        self.make_record(member, 120)
        self.start_game(token)

        self.assertEqual(self.withdraw(token, 'pw1234').status_code, 200)

        self.assertFalse(Member.objects.filter(id=member.id).exists())
        self.assertEqual(GameSession.objects.count(), 0)
        record = Record.objects.get()
        self.assertIsNone(record.member_id)
        self.assertEqual(record.nickname, 'Tester')
        self.assertDetail(self.call('get', '/api/me', token=token), 401)

        ranking = self.ranking()
        self.assertEqual(len(ranking), 1)
        self.assertTrue(ranking[0]['withdrawn'])

    def test_nickname_reuse_does_not_inherit_old_records(self):
        old, token = self.make_member('Tester')
        self.make_record(old, 300)
        self.withdraw(token, 'pw1234')

        new, _ = self.make_member('Tester')
        self.make_record(new, 100)

        ranking = self.ranking()
        self.assertEqual(
            [(row['score'], row['withdrawn']) for row in ranking],
            [(300, True), (100, False)],
        )

    def test_member_without_password_can_withdraw(self):
        member, token = self.make_member('옛회원', password=None)
        self.assertEqual(self.withdraw(token).status_code, 200)
        self.assertFalse(Member.objects.filter(id=member.id).exists())


class GameStartTests(ApiTestCase):
    def test_requires_login(self):
        response = self.call('post', '/api/games', {'duration': 60, 'gameMode': 'score'})
        self.assertDetail(response, 401)

    def test_issues_questions(self):
        _, token = self.make_member('Tester')
        expected = {'score': (60, 62), 'survival': (0, game_rules.SURVIVAL_QUESTION_COUNT)}
        for game_mode, (duration, count) in expected.items():
            with self.subTest(game_mode=game_mode):
                game = self.start_game(token, game_mode)
                self.assertEqual(game['duration'], duration)
                self.assertEqual(game['gameMode'], game_mode)
                self.assertEqual(len(game['questions']), count)
                for question in game['questions']:
                    self.assertEqual(
                        set(question), {'platePrefix', 'hangul', 'digits'}
                    )
                    self.assertEqual(len(question['digits']), 4)
                    self.assertTrue(all(0 <= d <= 9 for d in question['digits']))

    def test_score_mode_is_fixed_to_one_minute(self):
        _, token = self.make_member('Tester')
        # 게임 시간을 보내지 않아도, 60 을 보내도 1분 게임이다.
        for body in ({'gameMode': 'score'}, {'gameMode': 'score', 'duration': 60}):
            response = self.call('post', '/api/games', body, token=token)
            self.assertEqual(response.status_code, 201, response.content.decode())
            self.assertEqual(response.json()['duration'], 60)

    def test_survival_ignores_duration(self):
        _, token = self.make_member('Tester')
        response = self.call(
            'post', '/api/games', {'gameMode': 'survival', 'duration': 30}, token=token
        )
        self.assertEqual(response.status_code, 201, response.content.decode())
        self.assertEqual(response.json()['duration'], 0)

    def test_rejects_unplayable_settings(self):
        _, token = self.make_member('Tester')
        bad_bodies = {
            '30초는 없어졌다': ({'duration': 30, 'gameMode': 'score'}, '60초'),
            '없는 게임 시간': ({'duration': 45, 'gameMode': 'score'}, '60초'),
            '숫자가 아닌 게임 시간': ({'duration': 'abc', 'gameMode': 'score'}, '60초'),
            '없는 게임모드': ({'duration': 60, 'gameMode': 'hard'}, '게임모드'),
            '게임모드 누락': ({'duration': 60}, '게임모드'),
        }
        for label, (body, fragment) in bad_bodies.items():
            with self.subTest(label):
                self.assertDetail(
                    self.call('post', '/api/games', body, token=token), 400, fragment
                )
        self.assertEqual(GameSession.objects.count(), 0)

    def test_new_game_replaces_previous_one(self):
        _, token = self.make_member('Tester')
        first = self.start_game(token)
        second = self.start_game(token)
        self.assertEqual(
            list(GameSession.objects.values_list('id', flat=True)), [second['gameId']]
        )
        self.rewind(second['gameId'], 70)
        self.assertDetail(self.save(token, first['gameId'], []), 404, '찾을 수 없습니다')


class RecordSaveTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.member, self.token = self.make_member('Tester')

    def finished_game(self, digit_rows, duration=60):
        game = self.start_game(self.token)
        self.set_questions(game['gameId'], digit_rows)
        self.rewind(game['gameId'], duration + 4)
        return game['gameId']

    def test_server_grades_the_game(self):
        game_id = self.finished_game([NORMAL, HARD, NORMAL, HARD, NORMAL, HARD])
        answers = [
            {'answer': 10, 'time': 1.0},    # 보통 정답   +10
            {'answer': 30, 'time': 2.0},    # 어려움 정답 +15
            {'answer': 11, 'time': 1.5},    # 보통 오답   -20
            {'answer': 11, 'time': 0.5},    # 어려움 오답 -10
            {'answer': None, 'time': 5},    # 보통 시간 초과   -20
            {'answer': None, 'time': 5},    # 어려움 시간 초과 -10
        ]
        response = self.save(self.token, game_id, answers)
        self.assertEqual(response.status_code, 201, response.content.decode())
        data = response.json()

        self.assertEqual(data['nickname'], 'Tester')
        self.assertFalse(data['withdrawn'])
        self.assertEqual(data['duration'], 60)
        self.assertEqual(data['gameMode'], 'score')
        self.assertEqual(data['correct'], 2)
        self.assertEqual(data['wrong'], 4)
        self.assertEqual(data['score'], 10 + 15 - 20 - 10 - 20 - 10)
        self.assertIsNone(data['survivalTime'])
        self.assertAlmostEqual(data['accuracy'], 2 / 6 * 100)
        self.assertAlmostEqual(data['averageResponseTime'], (1.0 + 2.0 + 1.5 + 0.5 + 5 + 5) / 6)

        record = Record.objects.get(id=data['id'])
        self.assertEqual(record.member_id, self.member.id)
        self.assertEqual(record.score, data['score'])

    def test_client_cannot_supply_its_own_score(self):
        game_id = self.finished_game([NORMAL])
        response = self.save(
            self.token, game_id, [{'answer': 3, 'time': 1.0}],
            score=999999, correct=500, accuracy=100,
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['score'], -20)
        self.assertEqual(response.json()['correct'], 0)

    def test_game_can_be_saved_only_once(self):
        game_id = self.finished_game([NORMAL])
        answers = [{'answer': 10, 'time': 1.0}]
        self.assertEqual(self.save(self.token, game_id, answers).status_code, 201)
        self.assertDetail(self.save(self.token, game_id, answers), 404)
        self.assertEqual(Record.objects.count(), 1)

    def test_empty_game_is_saved_with_zero_score(self):
        game_id = self.finished_game([NORMAL])
        data = self.save(self.token, game_id, []).json()
        self.assertEqual(
            (data['correct'], data['wrong'], data['score'], data['accuracy']),
            (0, 0, 0, 0.0),
        )

    def test_game_must_be_played_to_the_end(self):
        game = self.start_game(self.token)
        self.rewind(game['gameId'], 30)
        self.assertDetail(self.save(self.token, game['gameId'], []), 400, '끝까지')
        # 거부된 뒤에도 게임이 끝나면 저장할 수 있다.
        self.rewind(game['gameId'], 64)
        self.assertEqual(self.save(self.token, game['gameId'], []).status_code, 201)

    def test_save_window_expires(self):
        game = self.start_game(self.token)
        self.rewind(game['gameId'], 60 + SAVE_WINDOW_SECONDS + 10)
        self.assertDetail(self.save(self.token, game['gameId'], []), 400, '시간이 지났습니다')
        self.assertEqual(GameSession.objects.count(), 0)
        self.assertEqual(Record.objects.count(), 0)

    def test_other_member_cannot_save_the_game(self):
        game_id = self.finished_game([NORMAL])
        _, other_token = self.make_member('Other')
        self.assertDetail(self.save(other_token, game_id, []), 404)
        self.assertEqual(Record.objects.count(), 0)

    def test_more_answers_than_fit_in_the_game_time(self):
        # 60초 게임에서 5초씩 걸린 답이 20개(문제 사이 텀 포함 약 118초)는 불가능하다.
        game_id = self.finished_game([NORMAL] * 62)
        answers = [{'answer': 10, 'time': 5.0}] * 20
        self.assertDetail(self.save(self.token, game_id, answers), 400, '올바르지 않아')
        self.assertEqual(Record.objects.count(), 0)

    def test_fastest_possible_legit_game_is_accepted(self):
        # 문제당 0.5초 + 텀 1초 → 60초에 40문제까지 가능
        game_id = self.finished_game([NORMAL] * 62)
        answers = [{'answer': 10, 'time': 0.5}] * 40
        response = self.save(self.token, game_id, answers)
        self.assertEqual(response.status_code, 201, response.content.decode())
        self.assertEqual(response.json()['score'], 400)

    def test_more_answers_than_issued_questions(self):
        game_id = self.finished_game([NORMAL, NORMAL])
        answers = [{'answer': 10, 'time': 0.1}] * 3
        self.assertDetail(self.save(self.token, game_id, answers), 400)

    def test_malformed_answer_logs(self):
        bad_answer_lists = {
            'negative time': [{'answer': 10, 'time': -1}],
            'time over limit': [{'answer': 10, 'time': 9}],
            'answer too large': [{'answer': 100, 'time': 1}],
            'huge answer': [{'answer': 10 ** 30, 'time': 1}],
            'huge time': [{'answer': 10, 'time': 1e300}],
            'bool answer': [{'answer': True, 'time': 1}],
            'missing time': [{'answer': 10}],
            'missing answer': [{'time': 1}],
            'not an object': [5],
            'not a list': 'abc',
            'too many': [{'answer': 10, 'time': 0}] * 501,
        }
        for label, answers in bad_answer_lists.items():
            with self.subTest(label):
                game_id = self.finished_game([NORMAL] * 5)
                response = self.save(self.token, game_id, answers)
                self.assertDetail(response, 400)
        self.assertEqual(Record.objects.count(), 0)

    def test_missing_game_id(self):
        self.assertDetail(
            self.call('post', '/api/records', {'answers': []}, token=self.token), 400
        )

    def test_old_payload_with_client_score_is_rejected(self):
        legacy_payload = {
            'duration': 60, 'gameMode': 'score', 'correct': 0, 'wrong': 0,
            'accuracy': 100, 'score': 999999, 'averageResponseTime': 0,
        }
        self.assertDetail(
            self.call('post', '/api/records', legacy_payload, token=self.token), 400
        )
        self.assertEqual(Record.objects.count(), 0)


class SurvivalSaveTests(ApiTestCase):
    """생존모드: 50점으로 시작해 0점 이하가 되면 끝. 버틴 시간이 기록이다."""

    def setUp(self):
        super().setUp()
        self.member, self.token = self.make_member('Tester')

    def survival_game(self, digit_rows, seconds_ago=60):
        game = self.start_game(self.token, 'survival')
        self.set_questions(game['gameId'], digit_rows)
        self.rewind(game['gameId'], seconds_ago)
        return game['gameId']

    def test_server_grades_the_game(self):
        game_id = self.survival_game([NORMAL] * 10)
        answers = [
            {'answer': 10, 'time': 1.0},    # 정답 60점      (게임 시간  0.0 ~  1.0초)
            {'answer': 11, 'time': 2.0},    # 오답 40점      ( 2.0 ~  4.0)
            {'answer': None, 'time': 5},    # 시간 초과 20점 ( 5.0 ~ 10.0)
            {'answer': 10, 'time': 0.5},    # 정답 30점      (11.0 ~ 11.5)
            {'answer': 11, 'time': 1.0},    # 오답 10점      (12.5 ~ 13.5)
            {'answer': 11, 'time': 1.5},    # 오답 -10점     (14.5 ~ 16.0) → 탈락
        ]
        response = self.save(self.token, game_id, answers)
        self.assertEqual(response.status_code, 201, response.content.decode())
        data = response.json()

        self.assertEqual(data['gameMode'], 'survival')
        self.assertEqual(data['duration'], 0)
        self.assertAlmostEqual(data['survivalTime'], 16.0)
        self.assertEqual(data['correct'], 2)
        self.assertEqual(data['wrong'], 4)
        self.assertEqual(data['score'], 60)     # 게임 중 최고 점수
        self.assertAlmostEqual(data['accuracy'], 2 / 6 * 100)
        self.assertAlmostEqual(data['averageResponseTime'], 11 / 6)

        record = Record.objects.get(id=data['id'])
        self.assertEqual(record.member_id, self.member.id)
        self.assertAlmostEqual(record.survival_time, 16.0)
        self.assertEqual(GameSession.objects.count(), 0)

        self.assertEqual([row['id'] for row in self.ranking('survival')], [data['id']])
        self.assertEqual(self.ranking('score'), [])

    def test_score_of_exactly_zero_ends_the_game(self):
        game_id = self.survival_game([HARD] * 10)
        # 어려운 문제 오답은 -10점: 50 → 40 → 30 → 20 → 10 → 0
        answers = [{'answer': 1, 'time': 1.0}] * 5
        response = self.save(self.token, game_id, answers)
        self.assertEqual(response.status_code, 201, response.content.decode())
        self.assertAlmostEqual(response.json()['survivalTime'], 9.0)
        self.assertEqual(response.json()['score'], 50)

    def test_unfinished_game_is_rejected(self):
        game_id = self.survival_game([NORMAL] * 10)
        for answers in ([], [{'answer': 10, 'time': 1.0}], [{'answer': 11, 'time': 1.0}] * 2):
            with self.subTest(answers=len(answers)):
                self.assertDetail(self.save(self.token, game_id, answers), 400, '끝까지')
        self.assertEqual(Record.objects.count(), 0)
        # 거부된 뒤에도 끝까지 진행한 기록은 저장할 수 있다.
        response = self.save(self.token, game_id, [{'answer': 11, 'time': 1.0}] * 3)
        self.assertEqual(response.status_code, 201, response.content.decode())

    def test_answers_after_elimination_are_rejected(self):
        game_id = self.survival_game([NORMAL] * 10)
        answers = [{'answer': 11, 'time': 1.0}] * 3 + [{'answer': 10, 'time': 1.0}] * 4
        self.assertDetail(self.save(self.token, game_id, answers), 400, '올바르지 않아')
        self.assertEqual(Record.objects.count(), 0)

    def test_cannot_claim_more_time_than_really_passed(self):
        # 시간 초과 3번이면 5 + 1 + 5 + 1 + 5 = 17초를 버틴 기록인데, 게임을 시작한 지 5초밖에 안 됐다.
        game_id = self.survival_game([NORMAL] * 10, seconds_ago=5)
        answers = [{'answer': None, 'time': 5}] * 3
        self.assertDetail(self.save(self.token, game_id, answers), 400, '올바르지 않아')
        self.assertEqual(Record.objects.count(), 0)

        self.rewind(game_id, 20)
        response = self.save(self.token, game_id, answers)
        self.assertEqual(response.status_code, 201, response.content.decode())
        self.assertAlmostEqual(response.json()['survivalTime'], 17.0)

    def test_client_cannot_supply_its_own_survival_time(self):
        game_id = self.survival_game([NORMAL] * 10)
        response = self.save(
            self.token, game_id, [{'answer': 11, 'time': 0.5}] * 3,
            survivalTime=99999, score=99999,
        )
        self.assertEqual(response.status_code, 201)
        self.assertAlmostEqual(response.json()['survivalTime'], 3.5)
        self.assertEqual(response.json()['score'], 50)

    def test_answering_every_issued_question_ends_the_game(self):
        game_id = self.survival_game([NORMAL] * 3)
        response = self.save(self.token, game_id, [{'answer': 10, 'time': 1.0}] * 3)
        self.assertEqual(response.status_code, 201, response.content.decode())
        self.assertAlmostEqual(response.json()['survivalTime'], 5.0)
        self.assertEqual(response.json()['score'], 80)

    def test_game_can_be_saved_only_once(self):
        game_id = self.survival_game([NORMAL] * 10)
        answers = [{'answer': 11, 'time': 1.0}] * 3
        self.assertEqual(self.save(self.token, game_id, answers).status_code, 201)
        self.assertDetail(self.save(self.token, game_id, answers), 404)
        self.assertEqual(Record.objects.count(), 1)

    def test_other_member_cannot_save_the_game(self):
        game_id = self.survival_game([NORMAL] * 10)
        _, other_token = self.make_member('Other')
        answers = [{'answer': 11, 'time': 1.0}] * 3
        self.assertDetail(self.save(other_token, game_id, answers), 404)
        self.assertEqual(Record.objects.count(), 0)

    def test_save_window_expires(self):
        game_id = self.survival_game([NORMAL] * 10, seconds_ago=5 + SAVE_WINDOW_SECONDS + 20)
        answers = [{'answer': 11, 'time': 1.0}] * 3     # 5초를 버틴 기록
        self.assertDetail(self.save(self.token, game_id, answers), 400, '시간이 지났습니다')
        self.assertEqual(GameSession.objects.count(), 0)
        self.assertEqual(Record.objects.count(), 0)

    def test_only_best_survival_record_per_member(self):
        for wrong_time in (1.0, 3.0, 2.0):
            game_id = self.survival_game([NORMAL] * 10)
            response = self.save(self.token, game_id, [{'answer': 11, 'time': wrong_time}] * 3)
            self.assertEqual(response.status_code, 201, response.content.decode())

        ranking = self.ranking('survival')
        self.assertEqual(len(ranking), 1)
        self.assertAlmostEqual(ranking[0]['survivalTime'], 11.0)    # 3초씩 3문제 + 텀 2번


class RankingTests(ApiTestCase):
    def test_empty_ranking(self):
        self.assertEqual(self.ranking(), [])

    def test_invalid_query(self):
        self.assertDetail(self.call('get', '/api/records?duration=abc'), 422)
        self.assertDetail(self.call('get', '/api/records?duration=45'), 422)
        self.assertDetail(self.call('get', '/api/records?duration=30'), 422, '60초')
        self.assertDetail(self.call('get', '/api/records?duration=60&gameMode=hard'), 422)

    def test_defaults_to_one_minute_score_mode(self):
        member, _ = self.make_member('A')
        self.make_record(member, 100)
        for path in ('/api/records', '/api/records?duration=60', '/api/records?gameMode=score'):
            with self.subTest(path):
                response = self.call('get', path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual([row['score'] for row in response.json()], [100])

    def test_only_best_record_per_member(self):
        a, _ = self.make_member('A')
        b, _ = self.make_member('B')
        for score in (300, 500, 400):
            self.make_record(a, score)
        self.make_record(b, 350)

        self.assertEqual(
            [(row['nickname'], row['score']) for row in self.ranking()],
            [('A', 500), ('B', 350)],
        )

    def test_one_member_cannot_fill_the_board(self):
        flooder, _ = self.make_member('Flooder')
        for i in range(15):
            self.make_record(flooder, 1000 + i)
        others = []
        for i in range(12):
            member, _ = self.make_member(f'player{i}')
            self.make_record(member, 100 + i)
            others.append(member)

        ranking = self.ranking()
        self.assertEqual(len(ranking), 10)
        self.assertEqual(ranking[0]['nickname'], 'Flooder')
        self.assertEqual(ranking[0]['score'], 1014)
        self.assertEqual(len({row['nickname'] for row in ranking}), 10)
        self.assertEqual([row['score'] for row in ranking[1:]], list(range(111, 102, -1)))

    def test_tie_breakers(self):
        members = [self.make_member(name)[0] for name in ('A', 'B', 'C', 'D')]
        self.make_record(members[0], 100, accuracy=80.0, average=1.0, created_at=1)
        self.make_record(members[1], 100, accuracy=90.0, average=2.0, created_at=2)
        self.make_record(members[2], 100, accuracy=90.0, average=1.5, created_at=4)
        self.make_record(members[3], 100, accuracy=90.0, average=1.5, created_at=3)

        self.assertEqual([row['nickname'] for row in self.ranking()], ['D', 'C', 'B', 'A'])

    def test_modes_have_separate_rankings(self):
        member, _ = self.make_member('A')
        self.make_record(member, 100, duration=60)
        self.make_record(member, 200, duration=30)      # 30초 게임이 있던 때의 기록은 보이지 않는다
        self.make_survival_record(member, 75.5)

        self.assertEqual([row['score'] for row in self.ranking('score')], [100])
        self.assertEqual([row['survivalTime'] for row in self.ranking('survival')], [75.5])

    def test_survival_ranking_orders_by_survival_time(self):
        members = [self.make_member(name)[0] for name in ('A', 'B', 'C', 'D')]
        self.make_survival_record(members[0], 80.0, correct=10, created_at=1)
        self.make_survival_record(members[1], 120.5, correct=5, created_at=2)
        self.make_survival_record(members[2], 80.0, correct=12, created_at=4)   # 같은 시간이면 정답 수
        self.make_survival_record(members[3], 80.0, correct=12, created_at=3)   # 그다음은 먼저 세운 기록
        # 점수(최고 점수)가 아무리 높아도 순위에는 영향이 없다.
        self.make_record(members[0], 9999, duration=0, game_mode='survival',
                         survival_time=10.0)

        self.assertEqual(
            [(row['nickname'], row['survivalTime']) for row in self.ranking('survival')],
            [('B', 120.5), ('D', 80.0), ('C', 80.0), ('A', 80.0)],
        )

    def test_withdrawn_records_are_grouped_by_nickname(self):
        self.make_record(None, 100, nickname='옛회원')
        self.make_record(None, 200, nickname='옛회원')
        self.make_record(None, 150, nickname='다른옛회원')

        self.assertEqual(
            [(row['nickname'], row['score'], row['withdrawn']) for row in self.ranking()],
            [('옛회원', 200, True), ('다른옛회원', 150, True)],
        )


class ThrottleTests(ApiTestCase):
    def login(self, ip, nickname='Tester', password='wrong-pw'):
        return self.call(
            'post', '/api/login', {'nickname': nickname, 'password': password},
            HTTP_CF_CONNECTING_IP=ip,
        )

    def test_login_attempts_are_limited_per_ip(self):
        self.make_member('Tester')
        for _ in range(10):
            self.assertEqual(self.login('203.0.113.1').status_code, 401)
        self.assertDetail(self.login('203.0.113.1'), 429, '요청이 너무 많습니다')
        # 올바른 비밀번호여도 제한 중에는 거부된다.
        self.assertDetail(self.login('203.0.113.1', password='pw1234'), 429)
        # 다른 접속자는 영향받지 않는다.
        self.assertEqual(self.login('203.0.113.2', password='pw1234').status_code, 200)

    def test_login_attempts_are_limited_per_nickname(self):
        self.make_member('Tester')
        for i in range(30):
            self.assertEqual(self.login(f'198.51.100.{i}').status_code, 401)
        self.assertDetail(self.login('198.51.100.200'), 429)
        # 닉네임 대소문자를 바꿔도 같은 계정으로 센다.
        self.assertDetail(self.login('198.51.100.201', nickname='TESTER'), 429)

    def test_register_is_limited_per_ip(self):
        for i in range(10):
            response = self.call(
                'post', '/api/register',
                {'nickname': f'user{i}', 'password': 'pw1234'},
                HTTP_CF_CONNECTING_IP='203.0.113.9',
            )
            self.assertEqual(response.status_code, 201)
        response = self.call(
            'post', '/api/register',
            {'nickname': 'user-extra', 'password': 'pw1234'},
            HTTP_CF_CONNECTING_IP='203.0.113.9',
        )
        self.assertDetail(response, 429)
        self.assertEqual(Member.objects.count(), 10)


class GameRulesTests(SimpleTestCase):
    def test_is_hard(self):
        # 0·같은 숫자·보수 쌍이 없고 합이 20 이상
        self.assertTrue(game_rules.is_hard([6, 7, 8, 9]))
        self.assertTrue(game_rules.is_hard([2, 5, 6, 7]))    # 합이 정확히 20
        self.assertTrue(game_rules.is_hard([5, 7, 8, 9]))    # 5 가 하나뿐이면 보수 쌍이 없다
        self.assertTrue(game_rules.is_hard([9, 5, 8, 7]))    # 순서는 상관없다

        # 같은 숫자가 있으면 곱셈으로 풀리므로 보통 문제
        self.assertFalse(game_rules.is_hard([9, 9, 9, 8]))
        self.assertFalse(game_rules.is_hard([7, 7, 8, 9]))
        self.assertFalse(game_rules.is_hard([6, 6, 6, 6]))

        # 0 이 있으면 더할 숫자가 줄어드므로 보통 문제
        self.assertFalse(game_rules.is_hard([0, 3, 8, 9]))
        self.assertFalse(game_rules.is_hard([0, 9, 8, 7]))

        # 합이 작으면 보통 문제
        self.assertFalse(game_rules.is_hard([0, 1, 1, 2]))
        self.assertFalse(game_rules.is_hard([0, 0, 0, 0]))
        self.assertFalse(game_rules.is_hard([1, 2, 3, 4]))
        self.assertFalse(game_rules.is_hard([1, 5, 6, 7]))   # 합 19

        # 보수 쌍이 있으면 보통 문제
        self.assertFalse(game_rules.is_hard([5, 5, 9, 9]))
        self.assertFalse(game_rules.is_hard([8, 3, 9, 2]))   # 8 + 2
        self.assertFalse(game_rules.is_hard([4, 6, 7, 9]))   # 4 + 6
        self.assertFalse(game_rules.is_hard([1, 9, 0, 0]))

    def test_hard_questions_have_no_shortcut(self):
        combos = list(itertools.product(range(10), repeat=4))
        hard = [digits for digits in combos if game_rules.is_hard(digits)]
        self.assertEqual(len(hard), 648)                     # 10000개 중 6.5%
        self.assertEqual(len({tuple(sorted(digits)) for digits in hard}), 27)

        for digits in hard:
            self.assertNotIn(0, digits)
            self.assertEqual(len(set(digits)), 4)
            self.assertGreaterEqual(sum(digits), game_rules.HARD_MIN_SUM)
            for size in (2, 3):
                # 두 숫자로도, 세 숫자로도 10을 만들 수 없다.
                for picked in itertools.combinations(digits, size):
                    self.assertNotEqual(sum(picked), 10)

    def test_question_shape(self):
        for _ in range(200):
            question = game_rules.generate_question()
            self.assertIn(len(question['platePrefix']), (2, 3))
            self.assertTrue(question['platePrefix'].isdigit())
            self.assertIn(question['hangul'], game_rules.PLATE_HANGUL)
            self.assertEqual(len(question['digits']), 4)

    def test_question_count_covers_fastest_possible_game(self):
        self.assertEqual(game_rules.question_count('score', 60), 62)
        self.assertEqual(game_rules.question_count('survival'), game_rules.SURVIVAL_QUESTION_COUNT)

    def test_grade_scores(self):
        def score(digits, answer):
            question = {'platePrefix': '12', 'hangul': '가', 'digits': digits}
            return game_rules.grade([question], [{'answer': answer, 'time': 1.0}], 60).score

        self.assertEqual(score(NORMAL, 10), 10)
        self.assertEqual(score(HARD, 30), 15)
        self.assertEqual(score(LOW, 4), 10)         # 쉬운 조합은 가산점 없음
        self.assertEqual(score(LOW, 5), -20)
        self.assertEqual(score(REPEATED, 35), 10)   # 9998 도 가산점 없음
        self.assertEqual(score(REPEATED, 34), -20)
        self.assertEqual(score(NORMAL, 9), -20)
        self.assertEqual(score(HARD, 9), -10)
        self.assertEqual(score(NORMAL, None), -20)
        self.assertEqual(score(HARD, None), -10)

    def test_grade_rejects_impossible_pace(self):
        questions = [{'platePrefix': '12', 'hangul': '가', 'digits': NORMAL}] * 62
        with self.assertRaises(game_rules.InvalidGameLog):
            game_rules.grade(questions, [{'answer': 10, 'time': 0.0}] * 62, 30)

    def test_survival_limit_shrinks_as_time_passes(self):
        limit = game_rules.survival_limit_ms
        # 15초마다 0.5초씩, 1초까지
        self.assertEqual(limit(0), 5000)
        self.assertEqual(limit(14_999), 5000)
        self.assertEqual(limit(15_000), 4500)
        self.assertEqual(limit(30_000), 4000)
        self.assertEqual(limit(60_000), 3000)
        self.assertEqual(limit(119_999), 1500)
        self.assertEqual(limit(120_000), 1000)
        self.assertEqual(limit(10_000_000), 1000)

        limits = [limit(ms) for ms in range(0, 200_000, 500)]
        self.assertEqual(limits, sorted(limits, reverse=True))      # 늘어나는 일은 없다
        self.assertEqual(min(limits), game_rules.SURVIVAL_LIMIT_MIN_MS)

    def test_grade_survival_uses_the_shrinking_limit(self):
        questions = [{'platePrefix': '12', 'hangul': '가', 'digits': NORMAL}] * 20
        answers = (
            # 3초씩 걸려 4문제 정답: 게임 시간 0~3, 4~7, 8~11, 12~15초 → 90점
            [{'answer': 10, 'time': 3.0}] * 4
            # 다섯 번째 문제는 16초에 나온다 → 제한 4.5초. 시간 초과는 그 문제의 제한 시간만큼 걸린다.
            #   16.0 ~ 20.5 (70점), 21.5 ~ 26.0 (50점), 27.0 ~ 31.5 (30점)
            #   32.5초부터는 제한 4.0초: 32.5 ~ 36.5 (10점), 37.5 ~ 41.5 (-10점)
            + [{'answer': None, 'time': 5}] * 5
        )
        result = game_rules.grade_survival(questions, answers)

        self.assertAlmostEqual(result.survival_time, 41.5)
        self.assertEqual((result.correct, result.wrong), (4, 5))
        self.assertEqual(result.score, 90)
        self.assertAlmostEqual(result.average_response_time, (12 + 4.5 * 3 + 4.0 * 2) / 9)

    def test_grade_survival_clamps_answers_to_the_current_limit(self):
        questions = [{'platePrefix': '12', 'hangul': '가', 'digits': NORMAL}] * 20
        # 제한 시간보다 길게 걸렸다고 적어 보내도 생존 시간이 그만큼 늘어나지는 않는다.
        slow = game_rules.grade_survival(questions, [{'answer': 11, 'time': 5.5}] * 3)
        timeouts = game_rules.grade_survival(questions, [{'answer': None, 'time': 0}] * 3)
        self.assertAlmostEqual(slow.survival_time, 17.0)
        self.assertAlmostEqual(timeouts.survival_time, 17.0)

    def test_grade_survival_rejects_broken_logs(self):
        questions = [{'platePrefix': '12', 'hangul': '가', 'digits': NORMAL}] * 5
        wrong = {'answer': 11, 'time': 1.0}
        right = {'answer': 10, 'time': 1.0}

        with self.assertRaises(game_rules.UnfinishedGame):
            game_rules.grade_survival(questions, [])
        with self.assertRaises(game_rules.UnfinishedGame):
            game_rules.grade_survival(questions, [wrong, wrong])
        with self.assertRaises(game_rules.InvalidGameLog) as caught:
            game_rules.grade_survival(questions, [wrong, wrong, wrong, right])
        self.assertNotIsInstance(caught.exception, game_rules.UnfinishedGame)
        with self.assertRaises(game_rules.InvalidGameLog):
            game_rules.grade_survival(questions, [right] * 6)
