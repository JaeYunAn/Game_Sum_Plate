const STORAGE_KEY = 'numberAdditionRankingsV1';
const ACCOUNT_TOKEN_KEY = 'numberAdditionAccountTokenV1';

let currentAccount = null;

const DIFFICULTIES = {
  score: 5,
};

const DIFFICULTY_NAMES = {
  score: '점수모드',
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

const accountStatus = document.querySelector('#account-status');
const registerForm = document.querySelector('#register-form');
const registerNicknameInput = document.querySelector('#register-nickname');
const loginForm = document.querySelector('#login-form');
const loginNicknameInput = document.querySelector('#login-nickname');
const logoutButton = document.querySelector('#logout-button');
const accountFeedback = document.querySelector('#account-feedback');
const withdrawButton = document.querySelector('#withdraw-button');

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
const countdownOverlay = document.querySelector('#countdown-overlay');
const countdownNumber = document.querySelector('#countdown-number');
const answerInput = document.querySelector('#answer-input');

const rankingList = document.querySelector('#ranking-list');

const recordForm = document.querySelector('#record-form');
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
  difficulty: 'score',
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
let countdownInterval = null;


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
  clearInterval(countdownInterval);

  gameInterval = null;
  feedbackTimeout = null;
  countdownInterval = null;

  countdownOverlay.hidden = true;
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

    gameClock.textContent = formatClock(state.duration);
  } else {
    gameClockArea.hidden = true;
    timerLabel.textContent = '정답까지 걸린 시간';
  }

  showScreen('game');
  runStartCountdown();
}


// 게임 시작 전 카운트다운

function runStartCountdown() {
  clearInterval(countdownInterval);
  countdownInterval = null;

  state.answerLocked = true;
  answerInput.disabled = true;

  let count = 3;

  countdownOverlay.hidden = false;
  countdownNumber.textContent = String(count);

  countdownInterval = setInterval(() => {
    count -= 1;

    if (count > 0) {
      countdownNumber.textContent = String(count);
      return;
    }

    clearInterval(countdownInterval);
    countdownInterval = null;

    countdownOverlay.hidden = true;

    beginGameAfterCountdown();
  }, 1000);
}


function beginGameAfterCountdown() {
  if (!state.running) return;

  if (state.mode === 'timed') {
    state.gameEndsAt = performance.now() + state.duration * 1000;

    gameClock.textContent = formatClock(state.duration);

    gameInterval = setInterval(updateGameClock, 25);
  }

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
  }, 1000);
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
  }, 1000);
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
    }, 1000);
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

  const isMember = Boolean(currentAccount);

  recordForm.hidden = state.mode !== 'timed' || !isMember;

  document.querySelector('#save-record-button').disabled = false;

  saveFeedback.textContent =
    state.mode === 'timed' && !isMember
      ? '게스트 모드에서는 기록을 저장할 수 없습니다.'
      : '';

  resultRankingArea.hidden = true;

  showScreen('result');
}




// 회원 관리

function updateAccountUI() {
  if (currentAccount) {
    accountStatus.textContent = `현재 회원: ${currentAccount.nickname}`;
    registerForm.hidden = true;
    loginForm.hidden = true;
    logoutButton.hidden = false;
    withdrawButton.hidden = false;
  } else {
    accountStatus.textContent =
      '게스트 모드: 기록 조회만 가능합니다.';
    registerForm.hidden = false;
    loginForm.hidden = false;
    logoutButton.hidden = true;
    withdrawButton.hidden = true;
  }
}

async function refreshAccount() {
  const token = localStorage.getItem(ACCOUNT_TOKEN_KEY);

  if (!token) {
    currentAccount = null;
    updateAccountUI();
    return;
  }

  try {
    const response = await fetch('/api/me', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        localStorage.removeItem(ACCOUNT_TOKEN_KEY);
        currentAccount = null;
      }

      throw new Error('회원 정보를 확인하지 못했습니다.');
    }

    currentAccount = await response.json();
  } catch (error) {
    if (localStorage.getItem(ACCOUNT_TOKEN_KEY) === token) {
      accountFeedback.textContent = error.message;
    }
  }

  updateAccountUI();
}

async function registerAccount(event) {
  event.preventDefault();

  const nickname = registerNicknameInput.value.trim();

  if (!nickname) {
    accountFeedback.textContent = '닉네임을 입력하세요.';
    return;
  }

  try {
    const response = await fetch('/api/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ nickname }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || '회원가입에 실패했습니다.');
    }

    localStorage.setItem(ACCOUNT_TOKEN_KEY, data.token);

    currentAccount = {
      id: data.id,
      nickname: data.nickname,
    };

    registerForm.reset();

    accountFeedback.textContent = '회원가입이 완료되었습니다.';

    updateAccountUI();
  } catch (error) {
    accountFeedback.textContent = error.message;
  }
}

async function loginAccount(event) {
  event.preventDefault();

  const nickname = loginNicknameInput.value.trim();

  if (!nickname) {
    accountFeedback.textContent = '닉네임을 입력하세요.';
    return;
  }

  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ nickname }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || '로그인에 실패했습니다.');
    }

    localStorage.setItem(ACCOUNT_TOKEN_KEY, data.token);

    currentAccount = {
      id: data.id,
      nickname: data.nickname,
    };

    loginForm.reset();
    accountFeedback.textContent = '로그인되었습니다.';

    updateAccountUI();
  } catch (error) {
    accountFeedback.textContent = error.message;
  }
}


async function logoutAccount() {
  if (!currentAccount) return;

  const token = localStorage.getItem(ACCOUNT_TOKEN_KEY);

  try {
    const response = await fetch('/api/logout', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || '로그아웃에 실패했습니다.');
    }

    localStorage.removeItem(ACCOUNT_TOKEN_KEY);
    currentAccount = null;

    accountFeedback.textContent = '로그아웃되었습니다.';

    updateAccountUI();
  } catch (error) {
    accountFeedback.textContent = error.message;
  }
}


async function withdrawAccount() {
  if (!currentAccount) return;

  const confirmed = window.confirm(
    `${currentAccount.nickname} 회원을 탈퇴하시겠습니까?\n기존 게임 기록은 유지됩니다.`
  );

  if (!confirmed) return;

  const token = localStorage.getItem(ACCOUNT_TOKEN_KEY);

  try {
    const response = await fetch('/api/account', {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || '회원탈퇴에 실패했습니다.');
    }

    localStorage.removeItem(ACCOUNT_TOKEN_KEY);

    currentAccount = null;

    accountFeedback.textContent = '회원탈퇴가 완료되었습니다.';

    updateAccountUI();
  } catch (error) {
    accountFeedback.textContent = error.message;
  }
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

async function updateRanking() {
  const duration = Number(durationSelect.value);
  const difficulty = difficultySelect.value;

  try {
    const response = await fetch(
      `/api/records?duration=${duration}&gameMode=${difficulty}`
    );

    if (!response.ok) {
      throw new Error('기록 조회 실패');
    }

    const records = await response.json();

    renderRanking(rankingList, records);
  } catch (error) {
    renderRanking(rankingList, []);
    rankingList.querySelector('li').textContent =
      '서버에서 기록을 불러오지 못했습니다.';
  }
}


// 닉네임 입력 및 기록 저장

async function saveRecord(event) {
  event.preventDefault();

  if (state.recordSaved || state.mode !== 'timed' || !currentAccount) {
    return;
  }

  const token = localStorage.getItem(ACCOUNT_TOKEN_KEY);
  const saveButton = document.querySelector('#save-record-button');

  const total = state.correct + state.wrong;

  const accuracy = total > 0
    ? (state.correct / total) * 100
    : 0;

  const average = state.attempts > 0
    ? state.totalResponseTime / state.attempts
    : 0;

  const payload = {
    duration: state.duration,
    gameMode: state.difficulty,
    correct: state.correct,
    wrong: state.wrong,
    accuracy,
    score: state.score,
    averageResponseTime: average,
  };

  saveButton.disabled = true;

  try {
    const response = await fetch('/api/records', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || '기록 저장에 실패했습니다.');
    }

    state.recordSaved = true;
    state.currentRecordId = data.id;

    saveFeedback.textContent = '서버에 기록이 저장되었습니다.';

    resultRankingTitle.textContent =
      `${state.duration}초 / ${DIFFICULTY_NAMES[state.difficulty]} 순위표`;

    const rankingResponse = await fetch(
      `/api/records?duration=${state.duration}&gameMode=${state.difficulty}`
    );

    if (!rankingResponse.ok) {
      throw new Error('순위표 조회에 실패했습니다.');
    }

    const records = await rankingResponse.json();

    const rank = records.findIndex(
      (item) => item.id === data.id
    );

    saveFeedback.textContent = rank >= 0
      ? `${rank + 1}위로 기록이 저장되었습니다.`
      : '기록이 저장되었습니다. TOP 10에는 포함되지 않았습니다.';

    renderRanking(
      resultRankingList,
      records,
      data.id
    );

    resultRankingArea.hidden = false;

    await updateRanking();
  } catch (error) {
    saveFeedback.textContent = error.message;

    if (!state.recordSaved) {
      saveButton.disabled = false;
    }
  }
}


// 이벤트 등록

registerForm.addEventListener('submit', registerAccount);
loginForm.addEventListener('submit', loginAccount);
logoutButton.addEventListener('click', logoutAccount);
withdrawButton.addEventListener('click', withdrawAccount);

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

updateAccountUI();
refreshAccount();
updateSetupVisibility();
updateRanking();
