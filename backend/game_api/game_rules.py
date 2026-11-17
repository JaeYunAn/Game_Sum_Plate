"""게임 규칙과 서버 채점.

점수는 브라우저가 보낸 값을 믿지 않고, 서버가 발급한 문제와 제출된 답안 기록으로
여기서 다시 계산한다. 화면 표시용으로 app.js 의 RULES 에 같은 값이 있으므로,
규칙을 바꿀 때는 두 곳을 함께 고쳐야 한다.
"""

import random
from dataclasses import dataclass

GAME_MODES = ('score', 'survival')

# 점수모드: 정해진 시간 동안 점수를 모은다. 게임 시간은 1분으로 고정이다.
SCORE_DURATION = 60
DURATIONS = (SCORE_DURATION,)

QUESTION_LIMIT_SECONDS = 5      # 문제당 제한 시간 (생존모드는 여기서 시작해 줄어든다)
PAUSE_SECONDS = 1.0             # 정답/오답 표시 후 다음 문제까지의 텀
COUNTDOWN_SECONDS = 3           # 시작 전 카운트다운

SCORE_CORRECT = 10
SCORE_WRONG = -20               # 오답과 시간 초과

# "어려운 문제": 빨리 푸는 지름길이 하나도 없는 번호판. 아래를 모두 만족해야 한다.
#   - 0 이 없다                      (0 이 있으면 더할 숫자가 줄어든다)
#   - 네 숫자가 모두 다르다          (같은 숫자가 있으면 곱셈으로 풀린다. 예: 9998 = 9×3 + 8)
#   - 더해서 10이 되는 짝이 없다     (10 만들기를 쓸 수 없다)
#   - 합이 HARD_MIN_SUM 이상이다     (작은 숫자뿐인 조합 제외. 세 숫자로 10이 되는 조합도 함께 빠진다)
# 10000개 조합 중 648개(6.5%)가 해당한다. 숫자 구성으로는 27가지다.
HARD_MIN_SUM = 20
SCORE_HARD_BONUS = 5            # 어려운 문제 정답 시 추가 점수
SCORE_HARD_WRONG = -10          # 어려운 문제 오답·시간 초과 시 감점

# 생존모드: SURVIVAL_START_SCORE 점으로 시작해 점수가 0점 이하가 되면 끝난다.
# 점수 규칙은 점수모드와 같고, 얼마나 오래 버텼는지를 겨룬다.
# 문제당 제한 시간은 게임 시간이 SURVIVAL_STEP_INTERVAL_MS 만큼 지날 때마다
# SURVIVAL_LIMIT_STEP_MS 씩 줄어들어 SURVIVAL_LIMIT_MIN_MS 까지 내려간다.
# 게임 시간은 "응답 시간 + 문제 사이 텀"을 더한 값이라 브라우저와 서버가 똑같이 계산할 수 있다.
SURVIVAL_START_SCORE = 50
SURVIVAL_LIMIT_START_MS = QUESTION_LIMIT_SECONDS * 1000
SURVIVAL_LIMIT_STEP_MS = 500
SURVIVAL_STEP_INTERVAL_MS = 15_000
SURVIVAL_LIMIT_MIN_MS = 1000
# 한 판에 발급하는 문제 수. 사람이 도달하기 어려운 수이며, 모두 풀면 그 시점에 게임이 끝난다.
SURVIVAL_QUESTION_COUNT = 300

PAUSE_MS = int(PAUSE_SECONDS * 1000)

# 타이머 오차를 감안한 허용 범위
ANSWER_TIME_SLACK_SECONDS = 0.5
TOTAL_TIME_SLACK_SECONDS = 1.0

# 일반 자가용 번호판에 사용되는 한글 32개
PLATE_HANGUL = (
    '가', '나', '다', '라', '마',
    '거', '너', '더', '러', '머',
    '버', '서', '어', '저',
    '고', '노', '도', '로', '모',
    '보', '소', '오', '조',
    '구', '누', '두', '루', '무',
    '부', '수', '우', '주',
)


class InvalidGameLog(Exception):
    """제출된 답안 기록이 게임 규칙상 나올 수 없는 형태일 때."""


class UnfinishedGame(InvalidGameLog):
    """아직 끝나지 않은 게임의 답안 기록일 때(생존모드에서 탈락하기 전)."""


@dataclass(frozen=True)
class GameResult:
    correct: int
    wrong: int
    accuracy: float
    score: int                      # 점수모드: 최종 점수 / 생존모드: 게임 중 최고 점수
    average_response_time: float
    survival_time: float | None = None   # 생존모드에서만: 버틴 시간(초)


def is_hard(digits):
    """지름길이 없는 번호판인지. 조건은 HARD_MIN_SUM 위의 설명을 볼 것."""
    if 0 in digits or len(set(digits)) != len(digits):
        return False

    if sum(digits) < HARD_MIN_SUM:
        return False

    return not any(
        digits[i] + digits[j] == 10
        for i in range(len(digits))
        for j in range(i + 1, len(digits))
    )


def score_delta(digits, is_correct):
    """문제 하나의 점수 변화."""
    hard = is_hard(digits)

    if is_correct:
        return SCORE_CORRECT + (SCORE_HARD_BONUS if hard else 0)

    return SCORE_HARD_WRONG if hard else SCORE_WRONG


def generate_question(rng=random):
    # 구형(두 자리) 또는 현행(세 자리) 승용차 번호판
    if rng.random() < 0.5:
        prefix = f'{rng.randint(1, 69):02d}'
    else:
        prefix = str(rng.randint(100, 699))

    return {
        'platePrefix': prefix,
        'hangul': rng.choice(PLATE_HANGUL),
        'digits': [rng.randint(0, 9) for _ in range(4)],
    }


def question_count(game_mode, duration=SCORE_DURATION):
    """한 게임에서 풀 수 있는 문제 수의 상한.

    점수모드는 문제 사이에 최소 PAUSE_SECONDS 가 지나므로 duration / PAUSE + 1 개를 넘을 수 없다.
    """
    if game_mode == 'survival':
        return SURVIVAL_QUESTION_COUNT

    return int(duration / PAUSE_SECONDS) + 2


def generate_questions(game_mode, duration=SCORE_DURATION, rng=random):
    return [generate_question(rng) for _ in range(question_count(game_mode, duration))]


def _result(correct, wrong, score, total_time, survival_time=None):
    count = correct + wrong

    return GameResult(
        correct=correct,
        wrong=wrong,
        accuracy=(correct / count * 100) if count else 0.0,
        score=score,
        average_response_time=(total_time / count) if count else 0.0,
        survival_time=survival_time,
    )


def grade(questions, answers, duration):
    """점수모드 답안 기록을 채점한다.

    answers 는 questions 와 같은 순서이며 각 항목은
    {'answer': 정수 또는 None(시간 초과), 'time': 응답 시간(초)} 이다.
    """
    if len(answers) > len(questions):
        raise InvalidGameLog('발급된 문제 수보다 답안이 많습니다.')

    correct = 0
    wrong = 0
    score = 0
    total_time = 0.0

    for question, entry in zip(questions, answers):
        digits = question['digits']
        answer = entry['answer']

        if answer is None:
            spent = float(QUESTION_LIMIT_SECONDS)
            is_correct = False
        else:
            spent = min(float(entry['time']), float(QUESTION_LIMIT_SECONDS))
            is_correct = answer == sum(digits)

        total_time += spent
        score += score_delta(digits, is_correct)

        if is_correct:
            correct += 1
        else:
            wrong += 1

    count = len(answers)

    # 응답 시간과 문제 사이 텀을 모두 더하면 게임 시간을 넘을 수 없다.
    pauses = PAUSE_SECONDS * 0.95 * max(count - 1, 0)
    if total_time + pauses > duration + TOTAL_TIME_SLACK_SECONDS:
        raise InvalidGameLog('게임 시간 안에 풀 수 없는 문제 수입니다.')

    return _result(correct, wrong, score, total_time)


def survival_limit_ms(elapsed_ms):
    """생존모드에서 게임 시간이 elapsed_ms 일 때 나온 문제의 제한 시간(ms)."""
    steps = int(elapsed_ms) // SURVIVAL_STEP_INTERVAL_MS

    return max(
        SURVIVAL_LIMIT_MIN_MS,
        SURVIVAL_LIMIT_START_MS - steps * SURVIVAL_LIMIT_STEP_MS,
    )


def grade_survival(questions, answers):
    """생존모드 답안 기록을 채점한다. 답안 형식은 grade() 와 같다.

    점수가 0점 이하가 된 답안이 마지막 답안이어야 한다. 그 전에 끝난 기록은
    UnfinishedGame, 탈락한 뒤의 답안이 있으면 InvalidGameLog 를 던진다.
    """
    if len(answers) > len(questions):
        raise InvalidGameLog('발급된 문제 수보다 답안이 많습니다.')

    score = SURVIVAL_START_SCORE
    peak = score
    correct = 0
    wrong = 0
    total_spent_ms = 0
    clock_ms = 0        # 지금 문제가 나온 게임 시간
    ended_ms = 0        # 마지막 답안이 처리된 게임 시간

    for question, entry in zip(questions, answers):
        if score <= 0:
            raise InvalidGameLog('탈락한 뒤에 푼 문제가 있습니다.')

        digits = question['digits']
        answer = entry['answer']
        limit_ms = survival_limit_ms(clock_ms)

        if answer is None:
            spent_ms = limit_ms
            is_correct = False
        else:
            spent_ms = min(round(float(entry['time']) * 1000), limit_ms)
            is_correct = answer == sum(digits)

        score += score_delta(digits, is_correct)
        peak = max(peak, score)
        total_spent_ms += spent_ms

        if is_correct:
            correct += 1
        else:
            wrong += 1

        ended_ms = clock_ms + spent_ms
        clock_ms = ended_ms + PAUSE_MS

    # 탈락했거나, 발급된 문제를 모두 풀었을 때만 끝난 게임이다.
    if score > 0 and len(answers) < len(questions):
        raise UnfinishedGame('아직 끝나지 않은 게임입니다.')

    return _result(
        correct,
        wrong,
        peak,
        total_spent_ms / 1000,
        survival_time=ended_ms / 1000,
    )
