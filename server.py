import hashlib
import secrets
import sqlite3
import time
import uuid

from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / 'number_addition.db'

app = FastAPI(title='번호판 더하기')


@contextmanager
def database():
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys = ON')
    connection.execute('PRAGMA busy_timeout = 10000')

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_database():
    with database() as connection:
        connection.execute('PRAGMA journal_mode = WAL')

        connection.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nickname TEXT NOT NULL COLLATE NOCASE UNIQUE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at INTEGER NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                member_id INTEGER,
                nickname TEXT NOT NULL,
                duration INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                correct INTEGER NOT NULL,
                wrong INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                score INTEGER NOT NULL,
                average_response_time REAL NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (member_id)
                    REFERENCES members(id)
                    ON DELETE SET NULL
            )
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_records_ranking
            ON records (
                duration,
                difficulty,
                score DESC,
                accuracy DESC,
                average_response_time ASC,
                created_at ASC
            )
        """)


init_database()


class RegisterRequest(BaseModel):
    nickname: str = Field(min_length=1, max_length=16)


class RecordRequest(BaseModel):
    duration: Literal[30, 60]
    difficulty: Literal['easy', 'normal', 'hard', 'extreme']
    correct: int = Field(ge=0)
    wrong: int = Field(ge=0)
    accuracy: float = Field(ge=0, le=100)
    score: int
    averageResponseTime: float = Field(ge=0)


def hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def get_current_member(authorization: str | None = Header(default=None)):
    if not authorization:
        raise HTTPException(401, '회원 인증이 필요합니다.')

    scheme, _, token = authorization.partition(' ')

    if scheme.lower() != 'bearer' or not token.strip():
        raise HTTPException(401, '인증 정보가 올바르지 않습니다.')

    with database() as connection:
        member = connection.execute(
            'SELECT id, nickname FROM members WHERE token_hash = ?',
            (hash_token(token.strip()),)
        ).fetchone()

    if member is None:
        raise HTTPException(401, '유효하지 않은 회원 인증입니다.')

    return {
        'id': member['id'],
        'nickname': member['nickname'],
    }


@app.post('/api/register', status_code=201)
def register(payload: RegisterRequest):
    nickname = payload.nickname.strip()

    if not nickname or len(nickname) > 16:
        raise HTTPException(400, '닉네임은 1~16자로 입력하세요.')

    token = secrets.token_urlsafe(32)

    try:
        with database() as connection:
            connection.execute(
                """
                INSERT INTO members (nickname, token_hash, created_at)
                VALUES (?, ?, ?)
                """,
                (nickname, hash_token(token), int(time.time() * 1000))
            )
    except sqlite3.IntegrityError:
        raise HTTPException(409, '이미 사용 중인 닉네임입니다.')

    return {
        'nickname': nickname,
        'token': token,
    }


@app.get('/api/me')
def get_me(member=Depends(get_current_member)):
    return member


@app.delete('/api/account')
def withdraw_account(member=Depends(get_current_member)):
    with database() as connection:
        connection.execute(
            'DELETE FROM members WHERE id = ?',
            (member['id'],)
        )

    return {'message': '회원탈퇴가 완료되었습니다.'}


@app.post('/api/records', status_code=201)
def save_record(
    payload: RecordRequest,
    member=Depends(get_current_member)
):
    record = {
        'id': str(uuid.uuid4()),
        'nickname': member['nickname'],
        'duration': payload.duration,
        'difficulty': payload.difficulty,
        'correct': payload.correct,
        'wrong': payload.wrong,
        'accuracy': payload.accuracy,
        'score': payload.score,
        'averageResponseTime': payload.averageResponseTime,
        'createdAt': int(time.time() * 1000),
    }

    with database() as connection:
        connection.execute(
            """
            INSERT INTO records (
                id, member_id, nickname, duration, difficulty,
                correct, wrong, accuracy, score,
                average_response_time, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record['id'],
                member['id'],
                record['nickname'],
                record['duration'],
                record['difficulty'],
                record['correct'],
                record['wrong'],
                record['accuracy'],
                record['score'],
                record['averageResponseTime'],
                record['createdAt'],
            )
        )

    return record


@app.get('/api/records')
def get_records(
    duration: int = Query(default=60),
    difficulty: Literal['easy', 'normal', 'hard', 'extreme'] = Query(
        default='normal'
    )
):
    if duration not in (30, 60):
        raise HTTPException(422, '게임 시간은 30초 또는 60초여야 합니다.')

    with database() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM records
            WHERE duration = ? AND difficulty = ?
            ORDER BY
                score DESC,
                accuracy DESC,
                average_response_time ASC,
                created_at ASC
            LIMIT 10
            """,
            (duration, difficulty)
        ).fetchall()

    return [
        {
            'id': row['id'],
            'nickname': row['nickname'],
            'duration': row['duration'],
            'difficulty': row['difficulty'],
            'correct': row['correct'],
            'wrong': row['wrong'],
            'accuracy': row['accuracy'],
            'score': row['score'],
            'averageResponseTime': row['average_response_time'],
            'createdAt': row['created_at'],
        }
        for row in rows
    ]


@app.get('/api/health')
def health():
    return {'status': 'ok'}


@app.get('/')
def index():
    return FileResponse(BASE_DIR / 'index.html')


@app.get('/app.js')
def javascript():
    return FileResponse(
        BASE_DIR / 'app.js',
        media_type='text/javascript'
    )


@app.get('/style.css')
def stylesheet():
    return FileResponse(
        BASE_DIR / 'style.css',
        media_type='text/css'
    )
