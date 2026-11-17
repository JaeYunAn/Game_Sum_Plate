'use strict';

const ACCOUNT_TOKEN_KEY = 'numberAdditionAccountTokenV1';

// 게임 규칙. 기록은 서버가 같은 규칙으로 다시 채점하므로
// backend/game_api/game_rules.py 와 같은 값을 유지해야 한다.
const RULES = {
  scoreDuration: 60,      // 점수모드 게임 시간(초). 1분 고정
  questionLimit: 5,       // 문제당 제한 시간(초). 생존모드는 여기서 시작해 줄어든다
  pauseMs: 1000,          // 정답/오답 표시 후 다음 문제까지의 텀
  practiceRetryMs: 1500,  // 연습 모드 오답 후 다시 입력할 수 있을 때까지
  countdown: 3,           // 시작 전 카운트다운(초)
  correct: 10,
  wrong: -20,             // 오답과 시간 초과
  hardMinSum: 20,         // 어려운 문제가 되려면 네 숫자의 합이 이 값 이상이어야 한다
  hardBonus: 5,           // 어려운 문제 정답 시 추가 점수
  hardWrong: -10,         // 어려운 문제 오답·시간 초과 시 감점

  // 생존모드: survivalStartScore 점으로 시작해 0점 이하가 되면 끝난다.
  // 게임 시간이 survivalStepIntervalMs 만큼 지날 때마다 문제 제한 시간이
  // survivalLimitStepMs 씩 줄어 survivalLimitMinMs 까지 내려간다.
  survivalStartScore: 50,
  survivalLimitStepMs: 500,
  survivalStepIntervalMs: 15000,
  survivalLimitMinMs: 1000,
};

// 설정 화면에서 모드를 고르면 바로 아래에 보여 주는 한 줄 설명
const MODE_DESCRIPTIONS = {
  score: `${RULES.scoreDuration / 60}분 동안 문제당 ${RULES.questionLimit}초. ` +
    `정답 +${RULES.correct}점, 오답·시간 초과 ${RULES.wrong}점입니다.`,
  survival: `${RULES.survivalStartScore}점으로 시작해 0점 이하가 되면 끝납니다. ` +
    `${RULES.survivalStepIntervalMs / 1000}초마다 문제 제한 시간이 ` +
    `${RULES.survivalLimitStepMs / 1000}초씩 줄어듭니다. 오래 버텨 보세요.`,
  practice: '시간 제한과 점수 없이 연습합니다. 기록은 남지 않습니다.',
};

// 순위표 제목에 쓰는 모드 이름
const RANKING_TITLES = {
  score: `점수모드 · ${RULES.scoreDuration / 60}분`,
  survival: '생존모드',
};

const PASSWORD_MIN_LENGTH = 4;
const API_TIMEOUT_MS = 10000;
// 게임 시작 요청은 카운트다운(3초) 동안 처리된다. 그 뒤로도 응답이 없으면 저장 없이 진행한다.
const GAME_START_TIMEOUT_MS = 6000;

// 시간 바가 "얼마 안 남음" 색으로 바뀌는 기준(초)
const GAME_URGENT_SECONDS = 10;
const QUESTION_URGENT_SECONDS = 2;

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

const mainElement = document.querySelector('main');
const accountArea = document.querySelector('#account-area');
const setupScreen = document.querySelector('#setup-screen');
const gameScreen = document.querySelector('#game-screen');
const resultScreen = document.querySelector('#result-screen');

const accountStatus = document.querySelector('#account-status');
const guestForms = document.querySelector('#guest-forms');
const loginForm = document.querySelector('#login-form');
const loginNicknameInput = document.querySelector('#login-nickname');
const loginPasswordInput = document.querySelector('#login-password');
const registerForm = document.querySelector('#register-form');
const registerNicknameInput = document.querySelector('#register-nickname');
const registerPasswordInput = document.querySelector('#register-password');
const memberActions = document.querySelector('#member-actions');
const logoutButton = document.querySelector('#logout-button');
const withdrawButton = document.querySelector('#withdraw-button');
const passwordNotice = document.querySelector('#password-notice');
const withdrawForm = document.querySelector('#withdraw-form');
const withdrawPasswordInput = document.querySelector('#withdraw-password');
const withdrawCancelButton = document.querySelector('#withdraw-cancel');
const accountFeedback = document.querySelector('#account-feedback');

const gameSetup = document.querySelector('#game-setup');
const modeDescription = document.querySelector('#mode-description');
const rankingCaption = document.querySelector('#ranking-caption');
const rankingList = document.querySelector('#ranking-list');

const gameNotice = document.querySelector('#game-notice');
const gameStatus = document.querySelector('#game-status');
const gameClockLabel = document.querySelector('#game-clock-label');
const gameClock = document.querySelector('#game-clock');
const gameClockTrack = document.querySelector('#game-clock-track');
const gameClockBar = document.querySelector('#game-clock-bar');
const scoreArea = document.querySelector('#score-area');
const currentScore = document.querySelector('#current-score');
const licensePlate = document.querySelector('#license-plate');
const platePrefix = document.querySelector('#plate-prefix');
const plateHangul = document.querySelector('#plate-hangul');
const plateDigits = [1, 2, 3, 4].map(
  (position) => document.querySelector(`#suffix-digit-${position}`)
);
const questionAnnouncer = document.querySelector('#question-announcer');
const timerTrack = document.querySelector('#timer-track');
const timerBar = document.querySelector('#timer-bar');
const timerLabel = document.querySelector('#timer-label');
const timer = document.querySelector('#timer');
const answerForm = document.querySelector('#answer-form');
const answerInput = document.querySelector('#answer-input');
const answerSubmit = document.querySelector('#answer-submit');
const keypad = document.querySelector('#keypad');
const feedbackPanel = document.querySelector('#feedback-panel');
const feedbackIcon = document.querySelector('#feedback-icon');
const feedbackTitle = document.querySelector('#feedback');
const feedbackDetail = document.querySelector('#feedback-detail');
const countdownOverlay = document.querySelector('#countdown-overlay');
const countdownNumber = document.querySelector('#countdown-number');
const endButton = document.querySelector('#end-button');

const resultTitle = document.querySelector('#result-title');
const resultHero = document.querySelector('#result-hero');
const resultSurvivalStat = document.querySelector('#result-survival-stat');
const resultSurvival = document.querySelector('#result-survival');
const resultCorrect = document.querySelector('#result-correct');
const resultWrong = document.querySelector('#result-wrong');
const resultAccuracyStat = document.querySelector('#result-accuracy-stat');
const resultAccuracy = document.querySelector('#result-accuracy');
const resultScoreLabel = document.querySelector('#result-score-label');
const resultScore = document.querySelector('#result-score');
const resultAverage = document.querySelector('#result-average');
const recordForm = document.querySelector('#record-form');
const saveButton = document.querySelector('#save-record-button');
const saveFeedback = document.querySelector('#save-feedback');
const resultRankingArea = document.querySelector('#result-ranking-area');
const resultRankingTitle = document.querySelector('#result-ranking-title');
const resultRankingList = document.querySelector('#result-ranking-list');
const reviewArea = document.querySelector('#review-area');
const reviewTitle = document.querySelector('#review-title');
const reviewList = document.querySelector('#review-list');
const retryButton = document.querySelector('#retry-button');
const returnButton = document.querySelector('#return-button');

// 화면 키패드를 쓰는 환경(터치 기기, 좁은 화면). style.css 의 미디어 쿼리와 같은 조건이다.
const keypadMedia = window.matchMedia('(pointer: coarse), (max-width: 480px)');

let currentAccount = null;

const state = {
  running: false,
  runId: 0,               // 게임을 시작할 때마다 증가. 비동기 작업이 이전 게임 것인지 구분한다.
  started: false,         // 카운트다운이 끝나 첫 문제가 나왔는지
  playType: 'timed',      // 'timed'(점수모드·생존모드) | 'practice'(연습)
  gameMode: 'score',      // 'score' | 'survival'
  duration: RULES.scoreDuration,
  gameEndsAt: 0,          // 점수모드가 끝나는 시각

  questionStartedAt: 0,
  questionLimit: RULES.questionLimit,   // 지금 문제의 제한 시간(초). 생존모드에서는 점점 줄어든다
  currentQuestion: null,
  answerLocked: true,
  lockedAnswerValue: '',

  // 생존모드의 게임 시간(ms). 응답 시간과 문제 사이 텀만 더한 값이라
  // 서버가 답안 기록만으로 똑같이 계산할 수 있다.
  clockMs: 0,             // 지금 문제가 나온 게임 시간
  settledMs: 0,           // 마지막 답이 처리된 게임 시간
  settledAt: 0,           // 그때의 실제 시각(performance.now)
  survivalMs: 0,          // 결과 화면에 보여 줄 생존 시간
  peakScore: 0,           // 게임 중 최고 점수
  over: false,            // 탈락했거나 발급된 문제를 모두 풀었다

  // 서버에서 받은 게임 정보. 로그인 상태로 시작한 점수모드·생존모드 게임에만 있다.
  serverQuestions: null,
  questionIndex: 0,
  gameId: null,
  gameOwnerId: null,
  saveBlock: null,        // 저장할 수 없는 이유: 'guest' | 'expired' | 'unavailable'
  answers: [],            // 서버 채점용 답안 기록
  history: [],            // 결과 화면의 "틀린 문제" 표시용

  correct: 0,
  wrong: 0,
  score: 0,
  totalResponseTime: 0,

  endedEarly: false,
  recordSaved: false,
  saving: false,
};

let gameInterval = null;
let questionInterval = null;
let questionTimeout = null;
let feedbackTimeout = null;
let countdownInterval = null;
let resolveCountdown = null;
let rankingRequestId = 0;
// 설정 화면의 순위표가 보여 주는 모드. 연습에는 순위표가 없어 직전에 보던 것을 그대로 둔다.
let rankingMode = 'score';


// 공통 유틸리티

function randomInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function formatClock(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  return `${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}`;
}

// 생존 시간 표시. 예: 52.3초, 1분 52.3초
function formatSurvivalTime(seconds) {
  const tenths = Math.round(seconds * 10);
  const minutes = Math.floor(tenths / 600);
  const rest = ((tenths % 600) / 10).toFixed(1);

  return minutes > 0 ? `${minutes}분 ${rest}초` : `${rest}초`;
}

function createElement(tag, className, text = '') {
  const element = document.createElement(tag);

  element.className = className;
  element.textContent = text;

  return element;
}

// 설정 화면의 칩(라디오 버튼)에서 고른 값
function selectedOption(name) {
  return document.querySelector(`input[name="${name}"]:checked`).value;
}

// 'score' | 'survival' | 'practice'
function selectedMode() {
  return selectedOption('game-mode');
}

// type: 'info' | 'success' | 'error' — 색으로 성공과 실패를 구분한다.
function setFeedback(element, message, type = 'info') {
  element.textContent = message;
  element.classList.toggle('is-success', type === 'success');
  element.classList.toggle('is-error', type === 'error');
}

// 줄어드는 시간 바. ratio 는 남은 비율(0~1)
function setBar(element, ratio, urgent = false) {
  const clamped = Math.max(0, Math.min(1, ratio));

  element.style.transform = `scaleX(${clamped})`;
  element.classList.toggle('is-urgent', urgent);
}

// 점수와 문제 제한 시간이 있는 게임(점수모드·생존모드)인지
function isTimed() {
  return state.playType === 'timed';
}

function isSurvival() {
  return isTimed() && state.gameMode === 'survival';
}

function isCurrentRun(runId) {
  return state.running && state.runId === runId;
}

function clearQuestionTimers() {
  clearInterval(questionInterval);
  clearTimeout(questionTimeout);

  questionInterval = null;
  questionTimeout = null;
}

function finishCountdown() {
  clearInterval(countdownInterval);
  countdownInterval = null;

  if (resolveCountdown) {
    const resolve = resolveCountdown;
    resolveCountdown = null;
    resolve();
  }
}

function clearAllTimers() {
  clearQuestionTimers();
  clearInterval(gameInterval);
  clearTimeout(feedbackTimeout);

  gameInterval = null;
  feedbackTimeout = null;

  finishCountdown();
  countdownOverlay.hidden = true;
}

function showScreen(screen) {
  setupScreen.hidden = screen !== 'setup';
  gameScreen.hidden = screen !== 'game';
  resultScreen.hidden = screen !== 'result';

  // 회원 영역은 설정 화면에 보인다. 결과 화면에서는 다시 로그인해야 저장할 수 있는
  // 경우(로그인 만료 등)에만 updateSaveAvailability() 가 다시 보여 준다.
  accountArea.hidden = screen !== 'setup';
  document.body.classList.toggle('is-playing', screen === 'game');
}


// 서버 통신

class ApiError extends Error {
  constructor(message, status, sessionExpired = false) {
    super(message);
    this.name = 'ApiError';
    this.status = status;   // 응답을 받지 못했으면 0
    // 로그인이 풀려서 실패한 요청. (비밀번호가 틀린 로그인의 401 과는 다르다.)
    // 안내는 api() 가 이미 했으므로 호출한 쪽에서 다시 표시하지 않는다.
    this.sessionExpired = sessionExpired;
  }
}

let memoryToken = null;

// 사생활 보호 모드 등에서는 localStorage 를 쓸 수 없을 수 있다.
// 그때는 새로고침 전까지만 메모리에 보관한다.
function readToken() {
  try {
    return localStorage.getItem(ACCOUNT_TOKEN_KEY);
  } catch (error) {
    return memoryToken;
  }
}

function writeToken(token) {
  memoryToken = token;

  try {
    localStorage.setItem(ACCOUNT_TOKEN_KEY, token);
  } catch (error) {
    // 메모리에만 보관
  }
}

function clearToken() {
  memoryToken = null;

  try {
    localStorage.removeItem(ACCOUNT_TOKEN_KEY);
  } catch (error) {
    // 지울 것이 없음
  }
}

function fallbackErrorMessage(status) {
  if (status === 401) return '로그인이 필요합니다.';
  if (status === 404) return '요청한 대상을 찾을 수 없습니다.';
  if (status === 429) return '요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.';
  if (status >= 500) return '서버에 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.';

  return '요청을 처리하지 못했습니다.';
}

// 다른 기기에서 로그인했거나 로그아웃되어 토큰이 더 이상 유효하지 않을 때
function handleSessionExpired(usedToken) {
  if (readToken() === usedToken) {
    clearToken();
  }

  currentAccount = null;
  updateAccountUI();

  setFeedback(
    accountFeedback,
    '로그인이 만료되었습니다. 다른 기기에서 로그인했을 수 있습니다. 다시 로그인해 주세요.',
    'error'
  );
}

// 모든 API 호출이 거치는 곳. 실패하면 화면에 그대로 보여 줄 수 있는
// 한글 메시지를 담은 ApiError 를 던진다.
async function api(path, { method = 'GET', body, auth = false, timeoutMs = API_TIMEOUT_MS } = {}) {
  const headers = {};
  let token = null;

  if (auth) {
    token = readToken();

    if (!token) {
      currentAccount = null;
      updateAccountUI();
      setFeedback(accountFeedback, '로그인이 필요합니다.', 'error');
      throw new ApiError('로그인이 필요합니다.', 401, true);
    }

    headers.Authorization = `Bearer ${token}`;
  }

  const options = { method, headers };

  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    options.body = JSON.stringify(body);
  }

  const controller = new AbortController();
  const abortTimer = setTimeout(() => controller.abort(), timeoutMs);
  options.signal = controller.signal;

  let response;

  try {
    response = await fetch(path, options);
  } catch (error) {
    throw new ApiError('서버에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.', 0);
  } finally {
    clearTimeout(abortTimer);
  }

  // 서버가 꺼져 있을 때 프록시가 주는 오류(502)처럼 본문이 JSON 이 아닐 수 있다.
  let data = null;

  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }

  if (!response.ok) {
    const sessionExpired = response.status === 401 && auth;

    if (sessionExpired) {
      handleSessionExpired(token);
    }

    const detail = data && typeof data.detail === 'string' ? data.detail : '';

    throw new ApiError(
      detail || fallbackErrorMessage(response.status),
      response.status,
      sessionExpired
    );
  }

  if (data === null) {
    throw new ApiError('서버 응답을 해석하지 못했습니다.', response.status);
  }

  return data;
}


// 회원 영역의 로그인 / 회원가입 탭

function updateAccountTab() {
  const tab = selectedOption('account-tab');

  loginForm.hidden = tab !== 'login';
  registerForm.hidden = tab !== 'register';
}

function showLoginTab() {
  document.querySelector('input[name="account-tab"][value="login"]').checked = true;
  updateAccountTab();
}


// 설정 화면

function updateModeDescription() {
  modeDescription.textContent = MODE_DESCRIPTIONS[selectedMode()];
}


// 번호판 및 문제

// "어려운 문제"는 빨리 푸는 지름길이 하나도 없는 번호판이다. 아래를 모두 만족해야 한다.
//   - 0 이 없다                  (0 이 있으면 더할 숫자가 줄어든다)
//   - 네 숫자가 모두 다르다      (같은 숫자가 있으면 곱셈으로 풀린다. 예: 9998 = 9×3 + 8)
//   - 더해서 10이 되는 짝이 없다 (10 만들기를 쓸 수 없다)
//   - 합이 RULES.hardMinSum 이상 (작은 숫자뿐인 번호판 제외)
function isHardQuestion(digits) {
  if (digits.includes(0) || new Set(digits).size !== digits.length) return false;

  const sum = digits.reduce((total, digit) => total + digit, 0);
  if (sum < RULES.hardMinSum) return false;

  for (let i = 0; i < digits.length; i++) {
    for (let j = i + 1; j < digits.length; j++) {
      if (digits[i] + digits[j] === 10) return false;
    }
  }

  return true;
}

function buildQuestion({ platePrefix: prefix, hangul, digits }) {
  return {
    platePrefix: prefix,
    hangul,
    digits,
    sum: digits.reduce((total, digit) => total + digit, 0),
    hard: isHardQuestion(digits),
  };
}

// 게스트 게임과 연습 모드에서 쓰는 문제. 회원의 점수모드·생존모드 게임은 서버가 문제를 준다.
function generateLocalQuestion() {
  return buildQuestion({
    // 구형 승용차 번호판 또는 현행 승용차 번호판
    platePrefix: Math.random() < 0.5
      ? String(randomInt(1, 69)).padStart(2, '0')
      : String(randomInt(100, 699)),
    hangul: PLATE_HANGUL[randomInt(0, PLATE_HANGUL.length - 1)],
    digits: Array.from({ length: 4 }, () => randomInt(0, 9)),
  });
}

function takeNextQuestion() {
  if (!state.serverQuestions) {
    return generateLocalQuestion();
  }

  const raw = state.serverQuestions[state.questionIndex];
  state.questionIndex += 1;

  return raw ? buildQuestion(raw) : null;
}

function isValidQuestion(question) {
  return Boolean(question) &&
    typeof question.platePrefix === 'string' &&
    typeof question.hangul === 'string' &&
    Array.isArray(question.digits) &&
    question.digits.length === 4 &&
    question.digits.every(
      (digit) => Number.isInteger(digit) && digit >= 0 && digit <= 9
    );
}

function renderQuestion(question) {
  platePrefix.textContent = question.platePrefix;
  plateHangul.textContent = question.hangul;

  question.digits.forEach((digit, index) => {
    plateDigits[index].textContent = digit;
  });

  // 화면을 볼 수 없는 사용자에게도 숫자가 전달되도록 한다.
  const spoken = question.digits.join(', ');

  licensePlate.setAttribute(
    'aria-label',
    `자동차 번호판 ${question.platePrefix}${question.hangul} ${question.digits.join('')}. 뒤 네 자리는 ${spoken}`
  );
  questionAnnouncer.textContent = `뒤 네 자리: ${spoken}`;
}

function blankPlate() {
  platePrefix.textContent = '??';
  plateHangul.textContent = '?';

  plateDigits.forEach((element) => {
    element.textContent = '?';
  });

  licensePlate.setAttribute('aria-label', '자동차 번호판');
  questionAnnouncer.textContent = '';
}

// 입력창을 disabled 로 만들면 포커스를 잃어 모바일 키보드가 문제마다 닫힌다.
// 포커스는 그대로 두고 입력만 막는다.
function lockAnswer(locked) {
  state.answerLocked = locked;
  state.lockedAnswerValue = answerInput.value;
  answerInput.classList.toggle('is-locked', locked);
  keypad.classList.toggle('is-locked', locked);
}

// 정답이면 초록, 오답이면 빨강으로 입력창과 게임 영역 전체의 색을 잠깐 바꾼다.
// result: 'correct' | 'wrong' | null(원래대로)
function markAnswer(result) {
  answerInput.classList.toggle('is-correct', result === 'correct');
  answerInput.classList.toggle('is-wrong', result === 'wrong');
  mainElement.classList.toggle('flash-correct', result === 'correct');
  mainElement.classList.toggle('flash-wrong', result === 'wrong');
}

// 화면 아래에서 올라오는 정답/오답 안내
function showAnswerFeedback(result, title, detail = '') {
  feedbackTitle.textContent = title;
  feedbackDetail.textContent = detail;
  feedbackIcon.textContent = result === 'correct' ? '✓' : '✕';

  feedbackPanel.classList.toggle('is-success', result === 'correct');
  feedbackPanel.classList.toggle('is-error', result !== 'correct');
  feedbackPanel.classList.add('is-visible');

  markAnswer(result);
}

function hideAnswerFeedback() {
  feedbackPanel.classList.remove('is-visible');
  // 같은 문구가 이어져도 스크린리더가 다시 읽도록 비워 둔다.
  feedbackTitle.textContent = '';
  feedbackDetail.textContent = '';

  markAnswer(null);
}


// 게임 시작

async function requestGameSession(gameMode) {
  try {
    const data = await api('/api/games', {
      method: 'POST',
      auth: true,
      // 생존모드에는 정해진 게임 시간이 없다.
      body: gameMode === 'survival'
        ? { gameMode }
        : { gameMode, duration: RULES.scoreDuration },
      timeoutMs: GAME_START_TIMEOUT_MS,
    });

    const valid = typeof data.gameId === 'string' &&
      Array.isArray(data.questions) &&
      data.questions.length > 0 &&
      data.questions.every(isValidQuestion);

    if (!valid) {
      return { ok: false, sessionExpired: false };
    }

    return { ok: true, gameId: data.gameId, questions: data.questions };
  } catch (error) {
    return { ok: false, sessionExpired: Boolean(error.sessionExpired) };
  }
}

// 설정 화면에서 고른 값으로 게임을 시작한다. ("다시 하기"도 같은 설정으로 시작한다.)
async function startGame() {
  if (state.running) return;

  const runId = state.runId + 1;
  const mode = selectedMode();
  const startScore = mode === 'survival' ? RULES.survivalStartScore : 0;

  Object.assign(state, {
    running: true,
    runId,
    started: false,
    playType: mode === 'practice' ? 'practice' : 'timed',
    gameMode: mode === 'survival' ? 'survival' : 'score',
    duration: RULES.scoreDuration,
    gameEndsAt: 0,
    questionLimit: RULES.questionLimit,
    currentQuestion: null,
    clockMs: 0,
    settledMs: 0,
    settledAt: 0,
    survivalMs: 0,
    peakScore: startScore,
    over: false,
    serverQuestions: null,
    questionIndex: 0,
    gameId: null,
    gameOwnerId: null,
    saveBlock: null,
    answers: [],
    history: [],
    correct: 0,
    wrong: 0,
    score: startScore,
    totalResponseTime: 0,
    endedEarly: false,
    recordSaved: false,
    saving: false,
  });

  const timed = isTimed();
  const survival = isSurvival();

  hideAnswerFeedback();
  setFeedback(saveFeedback, '');
  delete saveFeedback.dataset.kind;
  resultRankingArea.hidden = true;
  gameNotice.hidden = true;

  // 연습 모드에는 전체 시간, 점수, 문제 제한 시간이 없다.
  gameStatus.hidden = !timed;
  scoreArea.hidden = !timed;
  timerTrack.hidden = !timed;

  // 점수모드는 남은 시간이 줄어드는 바, 생존모드는 버틴 시간을 보여 준다.
  gameClockLabel.textContent = survival ? '생존 시간' : '남은 시간';
  gameClockTrack.hidden = survival;
  gameClock.textContent = formatClock(survival ? 0 : state.duration);
  showScore();
  setBar(gameClockBar, 1);
  setBar(timerBar, 1);
  showQuestionLimit(false);
  timer.textContent = timed
    ? `${RULES.questionLimit.toFixed(2)}초`
    : '0.00초';

  blankPlate();
  answerInput.value = '';
  lockAnswer(true);

  showScreen('game');
  gameScreen.scrollIntoView({ block: 'start' });
  // 시작 버튼을 누른 흐름 안에서 포커스를 줘야 모바일에서 키보드가 열린다.
  answerInput.focus({ preventScroll: true });

  // 회원의 점수모드·생존모드 게임은 서버에서 문제를 받아 온다(카운트다운과 동시에 진행).
  let sessionRequest = null;
  let ownerId = null;

  if (timed) {
    if (currentAccount) {
      ownerId = currentAccount.id;
      sessionRequest = requestGameSession(state.gameMode);
    } else {
      state.saveBlock = 'guest';
    }
  }

  await runStartCountdown();
  if (!isCurrentRun(runId)) return;

  const session = sessionRequest ? await sessionRequest : null;
  if (!isCurrentRun(runId)) return;

  countdownOverlay.hidden = true;

  if (session && session.ok) {
    state.serverQuestions = session.questions;
    state.gameId = session.gameId;
    state.gameOwnerId = ownerId;
  } else if (session) {
    state.saveBlock = session.sessionExpired ? 'expired' : 'unavailable';
  }

  if (state.saveBlock) {
    gameNotice.textContent = state.saveBlock === 'guest'
      ? '게스트 모드: 이번 게임은 기록으로 저장되지 않습니다.'
      : state.saveBlock === 'expired'
        ? '로그인이 만료되어 이번 게임은 기록으로 저장되지 않습니다.'
        : '서버에서 게임 정보를 받지 못해 이번 게임은 기록으로 저장되지 않습니다.';
    gameNotice.hidden = false;
  }

  beginGame();
}


// 게임 시작 전 카운트다운

function runStartCountdown() {
  return new Promise((resolve) => {
    let count = RULES.countdown;

    resolveCountdown = resolve;
    countdownOverlay.hidden = false;
    countdownNumber.textContent = String(count);

    countdownInterval = setInterval(() => {
      count -= 1;

      if (count > 0) {
        countdownNumber.textContent = String(count);
        return;
      }

      // 서버 응답을 아직 기다리는 중이면 이 표시가 잠깐 보인다.
      countdownNumber.textContent = '…';
      finishCountdown();
    }, 1000);
  });
}

function beginGame() {
  state.started = true;

  if (isSurvival()) {
    gameInterval = setInterval(updateGameClock, 50);
  } else if (isTimed()) {
    state.gameEndsAt = performance.now() + state.duration * 1000;
    gameClock.textContent = formatClock(state.duration);
    gameInterval = setInterval(updateGameClock, 25);
  }

  startNextQuestion();
}


// 생존모드

// 게임 시간이 clockMs 일 때 나온 문제의 제한 시간(ms). 서버의 survival_limit_ms 와 같다.
function survivalLimitMs(clockMs) {
  const steps = Math.floor(clockMs / RULES.survivalStepIntervalMs);

  return Math.max(
    RULES.survivalLimitMinMs,
    RULES.questionLimit * 1000 - steps * RULES.survivalLimitStepMs
  );
}

// 지금까지 버틴 게임 시간(ms)
function survivalClockMs() {
  if (state.over || !state.currentQuestion) {
    return state.settledMs;
  }

  const now = performance.now();

  if (state.answerLocked) {
    // 문제 사이의 텀: 다음 문제는 정확히 pauseMs 뒤의 게임 시간에 나온 것으로 계산한다.
    return state.settledMs + Math.min(now - state.settledAt, RULES.pauseMs);
  }

  return state.clockMs +
    Math.min(now - state.questionStartedAt, state.questionLimit * 1000);
}

function showScore() {
  currentScore.textContent = `${state.score}점`;
  // 생존모드에서 한 번만 더 틀리면 끝나는 점수는 경고색으로 보여 준다.
  scoreArea.classList.toggle(
    'is-danger',
    isSurvival() && state.score <= -RULES.wrong
  );
}

// 문제 제한 시간 안내. 생존모드에서는 지금 제한 시간을 함께 적고, 방금 줄었으면 강조한다.
function showQuestionLimit(shrunk) {
  if (!isTimed()) {
    timerLabel.textContent = '걸린 시간';
  } else if (isSurvival()) {
    timerLabel.textContent = `문제 제한 시간 ${state.questionLimit.toFixed(1)}초`;
  } else {
    timerLabel.textContent = '문제 제한 시간';
  }

  timerLabel.classList.toggle('is-shrunk', shrunk);
}


// 전체 게임 시간

function updateGameClock() {
  if (!state.running) return;

  if (isSurvival()) {
    gameClock.textContent = formatClock(Math.floor(survivalClockMs() / 1000));
    return;
  }

  const remaining = (state.gameEndsAt - performance.now()) / 1000;

  if (remaining <= 0) {
    finishTimedGame();
    return;
  }

  gameClock.textContent = formatClock(Math.ceil(remaining));
  setBar(
    gameClockBar,
    remaining / state.duration,
    remaining <= GAME_URGENT_SECONDS
  );
}


// 다음 문제

function startNextQuestion() {
  if (!state.running) return;

  if (scoreTimeIsUp()) {
    finishTimedGame();
    return;
  }

  clearQuestionTimers();
  clearTimeout(feedbackTimeout);
  feedbackTimeout = null;

  const question = takeNextQuestion();

  if (!question) {
    // 서버가 준 문제를 모두 풀었다. 문제 수는 넉넉히 발급되므로 정상적으로는 오지 않는다.
    state.over = true;
    finishTimedGame();
    return;
  }

  if (isSurvival()) {
    // 이 문제가 나온 게임 시간 = 앞 문제가 끝난 시간 + 텀. 그 시간에 맞는 제한 시간을 적용한다.
    const first = state.history.length === 0;
    const previousLimit = state.questionLimit;

    state.clockMs = first ? 0 : state.settledMs + RULES.pauseMs;
    state.questionLimit = survivalLimitMs(state.clockMs) / 1000;
    showQuestionLimit(!first && state.questionLimit < previousLimit);
  }

  state.currentQuestion = question;
  state.questionStartedAt = performance.now();

  hideAnswerFeedback();
  renderQuestion(question);

  answerInput.value = '';
  lockAnswer(false);
  answerInput.focus({ preventScroll: true });

  updateQuestionClock();
  questionInterval = setInterval(updateQuestionClock, 25);

  if (isTimed()) {
    questionTimeout = setTimeout(
      handleQuestionTimeout,
      state.questionLimit * 1000
    );
  }
}

// 점수모드의 게임 시간이 다 됐는지. (생존모드는 시간이 아니라 점수로 끝난다.)
function scoreTimeIsUp() {
  return isTimed() && !isSurvival() && performance.now() >= state.gameEndsAt;
}


// 문제별 시간 표시

function updateQuestionClock() {
  if (!state.running) return;

  const elapsed = (performance.now() - state.questionStartedAt) / 1000;

  if (isTimed()) {
    const limit = state.questionLimit;
    const remaining = Math.max(0, limit - elapsed);

    timer.textContent = `${remaining.toFixed(2)}초`;
    setBar(
      timerBar,
      remaining / limit,
      // 제한 시간이 짧아지면 "얼마 안 남음" 기준도 함께 줄인다.
      remaining <= Math.min(QUESTION_URGENT_SECONDS, limit * 0.4)
    );
  } else {
    timer.textContent = `${elapsed.toFixed(2)}초`;
  }
}


// 정답 제출

function handleAnswer() {
  if (!state.running || !state.started || state.answerLocked) return;
  if (answerInput.value === '') return;

  const answer = Number(answerInput.value);

  if (isTimed()) {
    handleTimedAnswer(answer);
  } else {
    handlePracticeAnswer(answer);
  }
}


// 점수모드·생존모드의 정답, 오답, 시간 초과

function handleTimedAnswer(answer) {
  if (scoreTimeIsUp()) {
    finishTimedGame();
    return;
  }

  settleTimedQuestion(
    answer,
    (performance.now() - state.questionStartedAt) / 1000
  );
}

function handleQuestionTimeout() {
  if (!state.running || !isTimed() || state.answerLocked) return;

  if (scoreTimeIsUp()) {
    finishTimedGame();
    return;
  }

  settleTimedQuestion(null, state.questionLimit);
}

// answer 가 null 이면 시간 초과
function settleTimedQuestion(answer, elapsed) {
  const question = state.currentQuestion;
  const timedOut = answer === null;
  const isCorrect = !timedOut && answer === question.sum;
  // 서버가 같은 값으로 다시 계산할 수 있도록 응답 시간은 ms 단위 정수로 맞춘다.
  const limitMs = Math.round(state.questionLimit * 1000);
  const spentMs = timedOut
    ? limitMs
    : Math.min(Math.round(elapsed * 1000), limitMs);
  const spent = spentMs / 1000;

  lockAnswer(true);
  clearQuestionTimers();

  state.settledMs = state.clockMs + spentMs;
  state.settledAt = performance.now();
  state.totalResponseTime += spent;
  state.answers.push({ answer, time: spent });
  state.history.push({ question, answer, isCorrect });

  let delta;

  if (isCorrect) {
    delta = RULES.correct + (question.hard ? RULES.hardBonus : 0);
    state.correct += 1;
  } else {
    delta = question.hard ? RULES.hardWrong : RULES.wrong;
    state.wrong += 1;
  }

  state.score += delta;
  state.peakScore = Math.max(state.peakScore, state.score);

  // 생존모드는 점수가 0점 이하가 되면 끝난다.
  const eliminated = isSurvival() && state.score <= 0;

  if (eliminated) {
    state.over = true;
  }

  showScore();

  if (isCorrect) {
    showAnswerFeedback(
      'correct',
      '정답입니다!',
      question.hard ? `+${delta}점 · 어려운 문제였어요!` : `+${delta}점`
    );
  } else {
    const detail = question.hard
      ? `정답 ${question.sum} · ${delta}점 · 어렵긴 했어요...`
      : `정답 ${question.sum} · ${delta}점`;

    showAnswerFeedback(
      'wrong',
      timedOut ? '시간 초과!' : '오답입니다!',
      eliminated ? `${detail} · 탈락` : detail
    );
  }

  // 탈락했으면 마지막 안내를 잠깐 보여 준 뒤 결과 화면으로 넘어간다.
  feedbackTimeout = setTimeout(
    eliminated ? () => finishTimedGame() : startNextQuestion,
    RULES.pauseMs
  );
}


// 연습 모드의 정답 및 오답

function handlePracticeAnswer(answer) {
  const elapsed = (performance.now() - state.questionStartedAt) / 1000;
  const isCorrect = answer === state.currentQuestion.sum;

  lockAnswer(true);

  if (isCorrect) {
    clearQuestionTimers();

    timer.textContent = `${elapsed.toFixed(2)}초`;
    showAnswerFeedback('correct', '정답입니다!', `${elapsed.toFixed(2)}초 걸렸어요`);

    feedbackTimeout = setTimeout(startNextQuestion, RULES.pauseMs);
    return;
  }

  showAnswerFeedback('wrong', '오답입니다!', '다시 입력하세요');

  // 오답이어도 같은 문제의 시간 측정은 계속된다.
  feedbackTimeout = setTimeout(() => {
    if (!state.running) return;

    hideAnswerFeedback();
    answerInput.value = '';
    lockAnswer(false);
    answerInput.focus({ preventScroll: true });
  }, RULES.practiceRetryMs);
}


// 게임 종료

// manual: 사용자가 "게임 종료" 버튼으로 끝낸 경우
function finishTimedGame(manual = false) {
  if (!state.running) return;

  const beforeStart = !state.started;
  // 점수모드는 게임 시간이 다 됐을 때, 생존모드는 탈락했을 때가 "끝까지 진행한" 게임이다.
  const finished = isSurvival()
    ? state.over
    : performance.now() >= state.gameEndsAt;

  state.endedEarly = manual && (beforeStart || !finished);
  state.survivalMs = isSurvival() && !beforeStart ? survivalClockMs() : 0;
  state.running = false;

  clearAllTimers();
  lockAnswer(true);
  hideAnswerFeedback();

  if (beforeStart) {
    // 카운트다운 중에 종료하면 보여 줄 결과가 없다.
    showScreen('setup');
    return;
  }

  displayResults();
}

function endPractice() {
  if (!state.running) return;

  state.running = false;

  clearAllTimers();
  lockAnswer(true);
  hideAnswerFeedback();

  showScreen('setup');
}


// 결과 화면

// survivalTime 이 있으면 생존모드 결과: 생존 시간과 최고 점수를 크게 보여 준다.
function showResultStats({ correct, wrong, accuracy, score, average, survivalTime = null }) {
  const survival = survivalTime !== null;

  resultHero.classList.toggle('is-survival', survival);
  resultSurvivalStat.hidden = !survival;
  resultAccuracyStat.hidden = survival;
  resultScoreLabel.textContent = survival ? '최고 점수' : '점수';

  if (survival) {
    resultSurvival.textContent = formatSurvivalTime(survivalTime);
  }

  resultCorrect.textContent = correct;
  resultWrong.textContent = wrong;
  resultAccuracy.textContent = `${accuracy.toFixed(1)}%`;
  resultScore.textContent = `${score}점`;
  resultAverage.textContent = `${average.toFixed(2)}초`;
}

// 틀린 문제(오답, 시간 초과)를 번호판, 풀이, 내 답과 함께 다시 보여 준다.
function renderReview() {
  const missed = state.history.filter((entry) => !entry.isCorrect);

  reviewList.replaceChildren();
  reviewArea.hidden = state.history.length === 0;

  if (state.history.length === 0) return;

  if (missed.length === 0) {
    reviewTitle.textContent = '틀린 문제 없음';
    reviewList.appendChild(
      createElement('li', 'review-empty', '푼 문제를 모두 맞혔습니다.')
    );
    return;
  }

  reviewTitle.textContent = `틀린 문제 ${missed.length}개`;

  missed.forEach(({ question, answer }) => {
    const item = document.createElement('li');
    const solution = createElement(
      'span',
      'review-sum',
      `${question.digits.join(' + ')} = `
    );

    solution.appendChild(createElement('strong', '', String(question.sum)));

    item.append(
      createElement(
        'span',
        'mini-plate',
        `${question.platePrefix}${question.hangul} ${question.digits.join('')}`
      ),
      solution,
      createElement(
        'span',
        'review-mine',
        answer === null ? '시간 초과' : `내 답 ${answer}`
      )
    );

    reviewList.appendChild(item);
  });
}

function displayResults() {
  const total = state.correct + state.wrong;

  const survival = isSurvival();

  showResultStats({
    correct: state.correct,
    wrong: state.wrong,
    accuracy: total > 0 ? (state.correct / total) * 100 : 0,
    score: survival ? state.peakScore : state.score,
    average: total > 0 ? state.totalResponseTime / total : 0,
    survivalTime: survival ? state.survivalMs / 1000 : null,
  });

  renderReview();

  saveButton.disabled = false;
  resultRankingArea.hidden = true;

  showScreen('result');
  updateSaveAvailability();

  mainElement.scrollIntoView({ block: 'start' });
  // 버튼에 포커스를 주면 게임 중 누르던 Enter 로 실수로 눌릴 수 있어 제목에 준다.
  resultTitle.focus({ preventScroll: true });
}

// 지금 이 결과를 저장할 수 있는지, 없다면 왜인지 보여 준다.
// 로그인 상태가 바뀔 때마다 다시 계산한다.
function updateSaveAvailability() {
  if (resultScreen.hidden || state.recordSaved) return;

  let blockMessage = '';
  // 다시 로그인하면 저장할 수 있는 경우에만 결과 화면에 회원 영역을 보여 준다.
  let needsLogin = false;

  if (state.endedEarly) {
    blockMessage = '중도 종료한 게임은 기록을 저장할 수 없습니다.';
  } else if (state.saveBlock === 'guest') {
    blockMessage = '게스트로 플레이한 게임은 저장할 수 없습니다. 기록을 남기려면 로그인한 뒤 플레이하세요.';
  } else if (state.saveBlock === 'expired') {
    blockMessage = '게임을 시작할 때 로그인이 만료되어 있어 이번 게임은 저장할 수 없습니다.';
  } else if (state.saveBlock) {
    blockMessage = '게임을 시작할 때 서버에서 게임 정보를 받지 못해 이번 게임은 저장할 수 없습니다.';
  } else if (!currentAccount) {
    blockMessage = '로그인이 필요합니다. 위에서 다시 로그인하면 이 기록을 저장할 수 있습니다.';
    needsLogin = true;
  } else if (currentAccount.id !== state.gameOwnerId) {
    blockMessage = '이 게임을 플레이한 계정으로 로그인해야 저장할 수 있습니다.';
    needsLogin = true;
  }

  accountArea.hidden = !needsLogin;
  recordForm.hidden = blockMessage !== '';

  if (blockMessage) {
    setFeedback(saveFeedback, blockMessage);
    saveFeedback.dataset.kind = 'block';
  } else if (saveFeedback.dataset.kind === 'block') {
    // 다시 로그인해서 저장할 수 있게 되었다.
    setFeedback(saveFeedback, '');
    delete saveFeedback.dataset.kind;
  }
}


// 회원 관리

function updateAccountUI() {
  const loggedIn = Boolean(currentAccount);

  accountStatus.textContent = loggedIn
    ? `현재 회원: ${currentAccount.nickname}`
    : '게스트 모드: 플레이와 기록 조회만 가능합니다.';

  guestForms.hidden = loggedIn;
  memberActions.hidden = !loggedIn;
  passwordNotice.hidden = !(loggedIn && currentAccount.hasPassword === false);

  if (loggedIn) {
    // 다음에 로그아웃되거나 로그인이 만료되면 로그인 폼부터 보이게 한다.
    showLoginTab();
  } else {
    closeWithdrawForm();
  }

  updateSaveAvailability();
}

async function refreshAccount() {
  if (!readToken()) {
    currentAccount = null;
    updateAccountUI();
    return;
  }

  try {
    const data = await api('/api/me', { auth: true });

    currentAccount = {
      id: data.id,
      nickname: data.nickname,
      hasPassword: data.hasPassword,
    };
  } catch (error) {
    // 로그인 만료면 api() 가 이미 게스트 상태로 바꾸고 안내했다.
    // 그 밖의 오류(서버 꺼짐 등)에서는 토큰을 지우지 않는다.
    if (!error.sessionExpired) {
      setFeedback(
        accountFeedback,
        `회원 정보를 확인하지 못했습니다. ${error.message}`,
        'error'
      );
    }
  }

  updateAccountUI();
}

// 요청하는 동안 폼의 버튼을 잠가 중복 제출을 막고, 실패 메시지를 표시한다.
async function submitAccountForm(form, action) {
  const buttons = form.querySelectorAll('button');

  buttons.forEach((button) => {
    button.disabled = true;
  });

  try {
    await action();
  } catch (error) {
    // 로그인 만료는 api() 가 이미 안내했다.
    if (!error.sessionExpired) {
      setFeedback(accountFeedback, error.message, 'error');
    }
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
    });
  }
}

function completeLogin(data, message) {
  writeToken(data.token);

  currentAccount = {
    id: data.id,
    nickname: data.nickname,
    hasPassword: data.hasPassword,
  };

  loginForm.reset();
  registerForm.reset();

  setFeedback(accountFeedback, message, 'success');
  updateAccountUI();
}

function registerAccount(event) {
  event.preventDefault();

  const nickname = registerNicknameInput.value.trim();
  const password = registerPasswordInput.value;

  if (!nickname) {
    setFeedback(accountFeedback, '닉네임을 입력하세요.', 'error');
    return;
  }

  if (password.length < PASSWORD_MIN_LENGTH) {
    setFeedback(
      accountFeedback,
      `비밀번호는 ${PASSWORD_MIN_LENGTH}자 이상 입력하세요.`,
      'error'
    );
    return;
  }

  submitAccountForm(registerForm, async () => {
    const data = await api('/api/register', {
      method: 'POST',
      body: { nickname, password },
    });

    completeLogin(data, '회원가입이 완료되었습니다.');
  });
}

function loginAccount(event) {
  event.preventDefault();

  const nickname = loginNicknameInput.value.trim();
  const password = loginPasswordInput.value;

  if (!nickname) {
    setFeedback(accountFeedback, '닉네임을 입력하세요.', 'error');
    return;
  }

  if (!password) {
    setFeedback(accountFeedback, '비밀번호를 입력하세요.', 'error');
    return;
  }

  submitAccountForm(loginForm, async () => {
    const data = await api('/api/login', {
      method: 'POST',
      body: { nickname, password },
    });

    completeLogin(
      data,
      data.passwordSet
        ? '로그인되었습니다. 방금 입력한 비밀번호가 이 계정의 비밀번호로 설정되었습니다.'
        : '로그인되었습니다.'
    );
  });
}

function logoutAccount() {
  if (!currentAccount) return;

  const token = readToken();

  // 서버 요청이 실패하더라도(토큰이 이미 무효, 서버 꺼짐 등)
  // 이 기기에서는 항상 로그아웃된다.
  clearToken();
  currentAccount = null;
  updateAccountUI();
  setFeedback(accountFeedback, '로그아웃되었습니다.', 'success');

  if (!token) return;

  fetch('/api/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => {
    // 이 기기의 로그아웃은 이미 끝났다.
  });
}

function openWithdrawForm() {
  if (!currentAccount) return;

  const needsPassword = currentAccount.hasPassword !== false;

  withdrawForm.reset();
  withdrawPasswordInput.hidden = !needsPassword;
  withdrawForm.hidden = false;

  if (needsPassword) {
    withdrawPasswordInput.focus();
  }
}

function closeWithdrawForm() {
  withdrawForm.reset();
  withdrawForm.hidden = true;
}

function withdrawAccount(event) {
  event.preventDefault();

  if (!currentAccount) return;

  const needsPassword = currentAccount.hasPassword !== false;
  const password = withdrawPasswordInput.value;

  if (needsPassword && !password) {
    setFeedback(accountFeedback, '비밀번호를 입력하세요.', 'error');
    return;
  }

  submitAccountForm(withdrawForm, async () => {
    await api('/api/account', {
      method: 'DELETE',
      auth: true,
      body: needsPassword ? { password } : {},
    });

    clearToken();
    currentAccount = null;
    updateAccountUI();
    setFeedback(accountFeedback, '회원탈퇴가 완료되었습니다.', 'success');

    updateRanking();
  });
}


// 순위표

function rankingPath(gameMode) {
  return gameMode === 'survival'
    ? '/api/records?gameMode=survival'
    : `/api/records?duration=${RULES.scoreDuration}&gameMode=score`;
}

function showRankingMessage(target, message) {
  target.replaceChildren(createElement('li', 'ranking-message', message));
}

function renderRanking(target, records, isCurrent = () => false) {
  if (records.length === 0) {
    showRankingMessage(target, '아직 기록이 없습니다.');
    return;
  }

  target.replaceChildren();

  records.forEach((record, index) => {
    const item = document.createElement('li');
    const name = createElement('span', 'rank-name', record.nickname);

    // 탈퇴한 회원의 기록은 같은 닉네임으로 새로 가입한 회원과 구분해서 보여 준다.
    if (record.withdrawn) {
      name.appendChild(createElement('small', 'rank-tag', '탈퇴'));
    }

    // 점수모드는 정답률과 점수, 생존모드는 정답 수와 버틴 시간을 보여 준다.
    const survival = record.gameMode === 'survival';

    item.append(
      createElement('span', 'rank-pos', `${index + 1}위`),
      name,
      createElement(
        'span',
        'rank-accuracy',
        survival
          ? `정답 ${record.correct}개`
          : `정답률 ${Number(record.accuracy).toFixed(1)}%`
      ),
      createElement(
        'span',
        'rank-score',
        survival
          ? formatSurvivalTime(Number(record.survivalTime))
          : `${record.score}점`
      )
    );

    if (index < 3) {
      item.classList.add('rank-top');
    }

    if (isCurrent(record)) {
      item.classList.add('rank-current');
    }

    target.appendChild(item);
  });
}

async function updateRanking() {
  const mode = selectedMode();

  if (mode !== 'practice') {
    rankingMode = mode;
  }

  const gameMode = rankingMode;
  const requestId = ++rankingRequestId;

  rankingCaption.textContent =
    `${RANKING_TITLES[gameMode]} TOP 10 (회원별 최고 기록)`;

  try {
    const records = await api(rankingPath(gameMode));

    // 그 사이 설정을 다시 바꿨다면 늦게 도착한 응답은 버린다.
    if (requestId !== rankingRequestId) return;

    renderRanking(rankingList, records);
  } catch (error) {
    if (requestId !== rankingRequestId) return;

    showRankingMessage(rankingList, '서버에서 기록을 불러오지 못했습니다.');
  }
}


// 기록 저장

async function saveRecord(event) {
  event.preventDefault();

  if (state.recordSaved || state.saving || !state.gameId) return;

  state.saving = true;
  saveButton.disabled = true;
  setFeedback(saveFeedback, '저장하는 중입니다...');
  saveFeedback.dataset.kind = 'save';

  let record;

  try {
    // 점수는 보내지 않는다. 서버가 발급한 문제와 이 답안 기록으로 직접 채점한다.
    record = await api('/api/records', {
      method: 'POST',
      auth: true,
      body: { gameId: state.gameId, answers: state.answers },
    });
  } catch (error) {
    state.saving = false;
    saveButton.disabled = false;

    if (error.sessionExpired) {
      // 로그인 만료: 다시 로그인하면 저장할 수 있다는 안내로 바꾼다.
      saveFeedback.dataset.kind = 'block';
      updateSaveAvailability();
    } else {
      setFeedback(saveFeedback, error.message, 'error');
    }

    return;
  }

  state.saving = false;
  state.recordSaved = true;
  recordForm.hidden = true;

  // 서버가 채점한 값이 최종 결과다.
  showResultStats({
    correct: record.correct,
    wrong: record.wrong,
    accuracy: record.accuracy,
    score: record.score,
    average: record.averageResponseTime,
    survivalTime: record.gameMode === 'survival' ? record.survivalTime : null,
  });

  await showSavedRanking(record);
  updateRanking();
}

async function showSavedRanking(record) {
  resultRankingTitle.textContent =
    `${RANKING_TITLES[record.gameMode] || record.gameMode} 순위표`;

  let records;

  try {
    records = await api(rankingPath(record.gameMode));
  } catch (error) {
    setFeedback(
      saveFeedback,
      '기록이 저장되었습니다. (순위표는 불러오지 못했습니다.)',
      'success'
    );
    return;
  }

  // 순위표에는 회원별 최고 기록만 올라간다.
  const isMine = (item) => !item.withdrawn && item.nickname === record.nickname;
  const rank = records.findIndex((item) => item.id === record.id);

  let message;

  if (rank >= 0) {
    message = `${rank + 1}위로 기록이 저장되었습니다.`;
  } else if (records.some(isMine)) {
    message = '기록이 저장되었습니다. 순위표에는 내 최고 기록이 표시됩니다.';
  } else {
    message = '기록이 저장되었습니다. TOP 10에는 들지 못했습니다.';
  }

  setFeedback(saveFeedback, message, 'success');
  renderRanking(resultRankingList, records, isMine);
  resultRankingArea.hidden = false;
}


// 화면 키패드 (터치 기기)

function pressKey(key) {
  if (state.answerLocked) return;

  if (key === 'back') {
    answerInput.value = answerInput.value.slice(0, -1);
  } else if (answerInput.value.length < 2) {
    answerInput.value += key;
  }
}

// 화면 키패드를 쓰는 기기에서는 입력창을 눌러도 기기 키보드가 올라오지 않게 한다.
function applyKeypadMode() {
  answerInput.setAttribute('inputmode', keypadMedia.matches ? 'none' : 'numeric');
}


// 이벤트 등록

registerForm.addEventListener('submit', registerAccount);
loginForm.addEventListener('submit', loginAccount);
logoutButton.addEventListener('click', logoutAccount);
withdrawButton.addEventListener('click', openWithdrawForm);
withdrawCancelButton.addEventListener('click', closeWithdrawForm);
withdrawForm.addEventListener('submit', withdrawAccount);

document.querySelectorAll('input[name="account-tab"]').forEach((radio) => {
  radio.addEventListener('change', updateAccountTab);
});

document.querySelectorAll('input[name="game-mode"]').forEach((radio) => {
  radio.addEventListener('change', () => {
    updateModeDescription();
    updateRanking();
  });
});

gameSetup.addEventListener('submit', (event) => {
  event.preventDefault();
  startGame();
});

// Enter 키, 제출 버튼, 화면 키패드의 제출 키가 모두 이 폼의 submit 으로 들어온다.
answerForm.addEventListener('submit', (event) => {
  event.preventDefault();
  // 버튼을 눌러도 입력창의 포커스를 유지한다.
  answerInput.focus({ preventScroll: true });
  handleAnswer();
});

// 버튼을 누를 때 입력창이 포커스를 잃지 않게 한다.
answerSubmit.addEventListener('mousedown', (event) => {
  event.preventDefault();
});

keypad.addEventListener('mousedown', (event) => {
  event.preventDefault();
});

keypad.addEventListener('click', (event) => {
  const key = event.target.closest('button[data-key]');

  if (key) {
    pressKey(key.dataset.key);
  }
});

answerInput.addEventListener('beforeinput', (event) => {
  if (state.answerLocked && event.cancelable) {
    event.preventDefault();
  }
});

answerInput.addEventListener('input', () => {
  if (state.answerLocked) {
    answerInput.value = state.lockedAnswerValue;
    return;
  }

  answerInput.value = answerInput.value.replace(/\D/g, '').slice(0, 2);
});

endButton.addEventListener('click', () => {
  if (isTimed()) {
    finishTimedGame(true);
  } else {
    endPractice();
  }
});

recordForm.addEventListener('submit', saveRecord);
retryButton.addEventListener('click', startGame);

returnButton.addEventListener('click', () => {
  showScreen('setup');
  updateRanking();
});

keypadMedia.addEventListener('change', applyKeypadMode);

// 다른 탭에서 로그인/로그아웃하면 이 탭의 회원 상태도 맞춘다.
window.addEventListener('storage', (event) => {
  if (event.key === ACCOUNT_TOKEN_KEY || event.key === null) {
    refreshAccount();
  }
});


// 최초 실행

applyKeypadMode();
updateAccountTab();
showScreen('setup');
updateAccountUI();
refreshAccount();
updateModeDescription();
updateRanking();
