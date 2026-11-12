const STORAGE_KEY = 'numberAdditionRankingsV1';

const DIFFICULTIES = {
  easy: 5,
  normal: 3,
  hard: 2,
  extreme: 1.75,
};

const DIFFICULTY_NAMES = {
  easy: '쉬움',
  normal: '보통',
  hard: '어려움',
  extreme: '극한',
};

// 일반 자가용 번호판에 사용되는 한글 32개
const PLATE_HANGUL = [
  '가', '나', '다', '라', '마',
  '거', '너', '더', '러', '머',
  '버', '서', '어', '저',
  '고', '노', '도', '로', '모',
  '보', '소', '오', '조',
  '구', '누', '두', '루', '무',
  '부', '수', '우', '주',
];

const setupScreen = document.querySelector('#setup-screen');
const gameScreen = document.querySelector('#game-screen');
const resultScreen = document.querySelector('#result-screen');

const gameSetup = document.querySelector('#game-setup');
const durationGroup = document.querySelector('#duration-group');
const difficultyGroup = document.querySelector('#difficulty-group');

const durationSelect = document.querySelector('#duration');
const difficultySelect = document.querySelector('#difficulty');

const gameClockArea = document.querySelector('#game-clock-area');
const gameClock = document.querySelector('#game-clock');
const timerLabel = document.querySelector('#timer-label');
const timer = document.querySelector('#timer');
const scoreArea = document.querySelector('#score-area');
const currentScore = document.querySelector('#current-score');

const feedback = document.querySelector('#feedback');
const answerInput = document.querySelector('#answer-input');

const rankingList = document.querySelector('#ranking-list');

const recordForm = document.querySelector('#record-form');
const nicknameInput = document.querySelector('#nickname');
const saveFeedback = document.querySelector('#save-feedback');

const resultCorrect = document.querySelector('#result-correct');
const resultWrong = document.querySelector('#result-wrong');
const resultAccuracy = document.querySelector('#result-accuracy');
const resultScore = document.querySelector('#result-score');
const resultAverage = document.querySelector('#result-average');

const resultRankingArea = document.querySelector('#result-ranking-area');
const resultRankingTitle = document.querySelector('#result-ranking-title');
const resultRankingList = document.querySelector('#result-ranking-list');

const state = {
  running: false,
  mode: 'timed',
  duration: 60,
  difficulty: 'normal',
  questionLimit: 3,
  gameEndsAt: 0,

  questionStartedAt: 0,
  currentQuestion: null,
  answerLocked: false,

  correct: 0,
  wrong: 0,
  score: 0,
  totalResponseTime: 0,
  attempts: 0,

  recordSaved: false,
  currentRecordId: null,
};

let gameInterval = null;
let questionInterval = null;
let questionTimeout = null;
let feedbackTimeout = null;


// 공통 유틸리티

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function shuffle(array) {
  const result = [...array];

  for (let i = result.length - 1; i > 0; i--) {
    const j = randomInt(0, i);
    [result[i], result[j]] = [result[j], result[i]];
  }

  return result;
}

function formatClock(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
}

function clearQuestionTimers() {
  clearInterval(questionInterval);
  clearTimeout(questionTimeout);

  questionInterval = null;
  questionTimeout = null;
}

function clearAllTimers() {
  clearQuestionTimers();
  clearInterval(gameInterval);
  clearTimeout(feedbackTimeout);

  gameInterval = null;
  feedbackTimeout = null;
}

function showScreen(screen) {
  setupScreen.hidden = screen !== 'setup';
  gameScreen.hidden = screen !== 'game';
  resultScreen.hidden = screen !== 'result';
}


// 설정 화면

function updateSetupVisibility() {
  const selectedMode = document.querySelector(
    'input[name="game-mode"]:checked'
  ).value;

  const isPractice = selectedMode === 'practice';

  durationGroup.hidden = isPractice;
  difficultyGroup.hidden = isPractice;
}

document.querySelectorAll('input[name="game-mode"]').forEach((radio) => {
  radio.addEventListener('change', updateSetupVisibility);
});


// 번호판 및 문제 생성

function generateQuestion() {
  // 구형 승용차 번호판 또는 현행 승용차 번호판
  const platePrefix = Math.random() < 0.5
    ? String(randomInt(1, 69)).padStart(2, '0')
    : String(randomInt(100, 699));

  const hangul = PLATE_HANGUL[
    randomInt(0, PLATE_HANGUL.length - 1)
  ];

  const digits = Array.from(
    { length: 4 },
    () => randomInt(0, 9)
  );

  const sum = digits.reduce((total, digit) => total + digit, 0);

  return {
    platePrefix,
    hangul,
    digits,
    sum,
  };
}

function renderQuestion() {
  const question = state.currentQuestion;

  document.querySelector('#plate-prefix').textContent =
    question.platePrefix;

  document.querySelector('#plate-hangul').textContent =
    question.hangul;

  question.digits.forEach((digit, index) => {
    document.querySelector(`#suffix-digit-${index + 1}`).textContent =
      digit;
  });

  answerInput.value = '';
  answerInput.disabled = false;
  answerInput.focus();
}


// 게임 시작

function startGame(event) {
  event.preventDefault();

  const selectedMode = document.querySelector(
    'input[name="game-mode"]:checked'
  ).value;

  state.mode = selectedMode;
  state.running = true;
  state.answerLocked = false;

  state.correct = 0;
  state.wrong = 0;
  state.score = 0;
  state.totalResponseTime = 0;
  state.attempts = 0;

  state.recordSaved = false;
  state.currentRecordId = null;

  feedback.textContent = '';
  saveFeedback.textContent = '';
  resultRankingArea.hidden = true;

  scoreArea.hidden = state.mode !== 'timed';
  currentScore.textContent = '0점';

  if (state.mode === 'timed') {
    state.duration = Number(durationSelect.value);
    state.difficulty = difficultySelect.value;
    state.questionLimit = DIFFICULTIES[state.difficulty];

    gameClockArea.hidden = false;
    timerLabel.textContent = '문제 제한 시간';

    state.gameEndsAt = performance.now() + state.duration * 1000;

    gameClock.textContent = formatClock(state.duration);

    gameInterval = setInterval(updateGameClock, 25);
  } else {
    gameClockArea.hidden = true;
    timerLabel.textContent = '정답까지 걸린 시간';
  }

  showScreen('game');
  startNextQuestion();
}


// 전체 게임 시간

function updateGameClock() {
  if (!state.running) return;

  const remaining = state.gameEndsAt - performance.now();

  if (remaining <= 0) {
    finishTimedGame();
    return;
  }

  gameClock.textContent = formatClock(
    Math.ceil(remaining / 1000)
  );
}


// 다음 문제

function startNextQuestion() {
  if (!state.running) return;

  if (
    state.mode === 'timed' &&
    performance.now() >= state.gameEndsAt
  ) {
    finishTimedGame();
    return;
  }

  clearQuestionTimers();
  clearTimeout(feedbackTimeout);

  feedbackTimeout = null;

  state.currentQuestion = generateQuestion();
  state.questionStartedAt = performance.now();
  state.answerLocked = false;

  feedback.textContent = '';

  renderQuestion();

  if (state.mode === 'practice') {
    timer.textContent = '0.00초';
  } else {
    updateQuestionClock();
  }

  questionInterval = setInterval(updateQuestionClock, 25);

  if (state.mode === 'timed') {
    questionTimeout = setTimeout(
      handleQuestionTimeout,
      state.questionLimit * 1000
    );
  }
}


// 문제별 시간 표시

function updateQuestionClock() {
  if (!state.running) return;

  const elapsed = (
    performance.now() - state.questionStartedAt
  ) / 1000;

  if (state.mode === 'practice') {
    timer.textContent = `${elapsed.toFixed(2)}초`;
  } else {
    const remaining = Math.max(
      0,
      state.questionLimit - elapsed
    );

    timer.textContent = `${remaining.toFixed(2)}초`;
  }
}


// 정답 선택

function handleAnswer() {
  if (!state.running || state.answerLocked) return;
  if (answerInput.value === '') return;

  const selectedAnswer = Number(answerInput.value);

  if (state.mode === 'practice') {
    handlePracticeAnswer(selectedAnswer);
  } else {
    handleTimedAnswer(selectedAnswer);
  }
}


// 시간 제한 모드의 정답 및 오답

function handleTimedAnswer(selectedAnswer) {
  if (performance.now() >= state.gameEndsAt) {
    finishTimedGame();
    return;
  }

  state.answerLocked = true;

  const elapsed = (
    performance.now() - state.questionStartedAt
  ) / 1000;

  state.attempts += 1;
  state.totalResponseTime += elapsed;

  clearQuestionTimers();

  const isCorrect = selectedAnswer === state.currentQuestion.sum;


  if (isCorrect) {
    state.correct += 1;
    state.score += 10;

    feedback.textContent = '정답입니다! +10점';
  } else {
    state.wrong += 1;
    state.score -= 20;

    feedback.textContent =
      `오답입니다! 정답: ${state.currentQuestion.sum} (-20점)`;
  }

  currentScore.textContent = `${state.score}점`;

  answerInput.disabled = true;

  feedbackTimeout = setTimeout(() => {
    if (state.running) {
      startNextQuestion();
    }
  }, 750);
}


// 제한 시간 초과

function handleQuestionTimeout() {
  if (!state.running || state.mode !== 'timed') return;
  if (state.answerLocked) return;

  if (performance.now() >= state.gameEndsAt) {
    finishTimedGame();
    return;
  }

  state.answerLocked = true;

  state.attempts += 1;
  state.wrong += 1;
  state.score -= 20;
  currentScore.textContent = `${state.score}점`;

  state.totalResponseTime += state.questionLimit;

  clearQuestionTimers();


  answerInput.disabled = true;

  feedback.textContent =
    `시간 초과! 정답: ${state.currentQuestion.sum} (-20점)`;

  feedbackTimeout = setTimeout(() => {
    if (state.running) {
      startNextQuestion();
    }
  }, 750);
}


// 연습 모드의 정답 및 오답

function handlePracticeAnswer(selectedAnswer) {
  state.answerLocked = true;

  const elapsed = (
    performance.now() - state.questionStartedAt
  ) / 1000;

  const isCorrect = selectedAnswer === state.currentQuestion.sum;


  answerInput.disabled = true;

  if (isCorrect) {
    clearQuestionTimers();

    timer.textContent = `${elapsed.toFixed(2)}초`;
    feedback.textContent = `정답! ${elapsed.toFixed(2)}초 소요`;

    feedbackTimeout = setTimeout(() => {
      if (state.running) {
        startNextQuestion();
      }
    }, 1500);
  } else {
    feedback.textContent = '오답입니다. 다시 선택하세요.';

    // 오답이어도 같은 문제의 시간 측정은 계속된다.
    feedbackTimeout = setTimeout(() => {
      if (!state.running) return;

      state.answerLocked = false;
      feedback.textContent = '';

      answerInput.disabled = false;
      answerInput.value = '';
      answerInput.focus();
    }, 1500);
  }
}


// 게임 종료

function finishTimedGame() {
  if (!state.running) return;

  state.running = false;

  clearAllTimers();

  gameClock.textContent = '00:00';

  displayResults();
}

function endPractice() {
  if (!state.running) return;

  state.running = false;

  clearAllTimers();

  showScreen('setup');
}


// 결과 화면

function displayResults() {
  const total = state.correct + state.wrong;

  const accuracy = total > 0
    ? (state.correct / total) * 100
    : 0;

  const average = state.attempts > 0
    ? state.totalResponseTime / state.attempts
    : 0;

  resultCorrect.textContent = state.correct;
  resultWrong.textContent = state.wrong;
  resultAccuracy.textContent = `${accuracy.toFixed(1)}%`;
  resultScore.textContent = `${state.score}점`;
  resultAverage.textContent = `${average.toFixed(2)}초`;

  nicknameInput.value = 'Player';
  nicknameInput.disabled = false;

  document.querySelector('#save-record-button').disabled = false;

  saveFeedback.textContent = '';
  resultRankingArea.hidden = true;

  showScreen('result');
}


// 로컬 순위 기록

function getRankings() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);

    if (!saved) return {};

    const parsed = JSON.parse(saved);

    return parsed && typeof parsed === 'object' &&
      !Array.isArray(parsed)
      ? parsed
      : {};
  } catch (error) {
    return {};
  }
}

function getRankingKey(duration, difficulty) {
  return `timed-${duration}-${difficulty}`;
}

function sortRankings(records) {
  return records.sort((a, b) => {
    return (
      b.score - a.score ||
      b.accuracy - a.accuracy ||
      a.averageResponseTime - b.averageResponseTime ||
      a.createdAt - b.createdAt
    );
  });
}

function renderRanking(target, records, currentRecordId = null) {
  target.replaceChildren();

  if (records.length === 0) {
    const item = document.createElement('li');
    item.textContent = '아직 기록이 없습니다.';
    target.appendChild(item);
    return;
  }

  records.forEach((record, index) => {
    const item = document.createElement('li');

    item.textContent =
      `${index + 1}위  ${record.nickname} | ` +
      `${record.score}점 | ` +
      `정답률 ${record.accuracy.toFixed(1)}%`;

    if (record.id === currentRecordId) {
      item.classList.add('rank-current');
    }

    target.appendChild(item);
  });
}

function updateRanking() {
  const duration = Number(durationSelect.value);
  const difficulty = difficultySelect.value;

  const key = getRankingKey(duration, difficulty);
  const rankings = getRankings();

  const records = sortRankings([
    ...(rankings[key] || []),
  ]);

  renderRanking(rankingList, records);
}


// 닉네임 입력 및 기록 저장

function saveRecord(event) {
  event.preventDefault();

  if (state.recordSaved || state.mode !== 'timed') return;

  const nickname = nicknameInput.value.trim() || 'Player';

  const total = state.correct + state.wrong;

  const accuracy = total > 0
    ? (state.correct / total) * 100
    : 0;

  const average = state.attempts > 0
    ? state.totalResponseTime / state.attempts
    : 0;

  const record = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    nickname,
    duration: state.duration,
    difficulty: state.difficulty,
    correct: state.correct,
    wrong: state.wrong,
    accuracy,
    score: state.score,
    averageResponseTime: average,
    createdAt: Date.now(),
  };

  const rankings = getRankings();
  const key = getRankingKey(state.duration, state.difficulty);

  const records = rankings[key] || [];

  records.push(record);

  const sortedRecords = sortRankings(records).slice(0, 10);

  rankings[key] = sortedRecords;

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rankings));

    state.recordSaved = true;
    state.currentRecordId = record.id;

    nicknameInput.disabled = true;
    document.querySelector('#save-record-button').disabled = true;

    const rank = sortedRecords.findIndex(
      (item) => item.id === record.id
    );

    saveFeedback.textContent = rank >= 0
      ? `${rank + 1}위로 기록이 저장되었습니다.`
      : '기록이 저장되었습니다. TOP 10에는 포함되지 않았습니다.';

    resultRankingTitle.textContent =
      `${state.duration}초 / ${DIFFICULTY_NAMES[state.difficulty]} 순위표`;

    renderRanking(
      resultRankingList,
      sortedRecords,
      record.id
    );

    resultRankingArea.hidden = false;

    updateRanking();
  } catch (error) {
    saveFeedback.textContent =
      '기록을 저장하지 못했습니다. 브라우저 저장 기능을 확인하세요.';
  }
}


// 이벤트 등록

gameSetup.addEventListener('submit', startGame);

answerInput.addEventListener('input', () => {
  answerInput.value = answerInput.value.replace(/\D/g, '').slice(0, 2);
});

answerInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    event.preventDefault();
    handleAnswer();
  }
});

document.querySelector('#end-button').addEventListener('click', () => {
  if (state.mode === 'practice') {
    endPractice();
  } else {
    finishTimedGame();
  }
});

recordForm.addEventListener('submit', saveRecord);

durationSelect.addEventListener('change', updateRanking);
difficultySelect.addEventListener('change', updateRanking);

document.querySelector('#return-button').addEventListener('click', () => {
  showScreen('setup');
  updateRanking();
});


// 최초 실행

updateSetupVisibility();
updateRanking();
