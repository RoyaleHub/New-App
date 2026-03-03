const state = {
  playerName: localStorage.getItem("laerquest_player") || "",
  currentSubject: null,
  questions: [],
  questionIndex: 0,
  answeredCurrent: false,
};

const subjectsEl = document.getElementById("subjects");
const template = document.getElementById("subjectTemplate");
const gameSection = document.getElementById("gameSection");
const gameTitle = document.getElementById("gameTitle");
const lessonVideo = document.getElementById("lessonVideo");
const quiz = document.getElementById("quiz");
const feedback = document.getElementById("feedback");
const nextQuestionBtn = document.getElementById("nextQuestion");
const closeGameBtn = document.getElementById("closeGame");
const xpEl = document.getElementById("xp");
const levelEl = document.getElementById("level");
const streakEl = document.getElementById("streak");
const playerNameInput = document.getElementById("playerName");
const savePlayerBtn = document.getElementById("savePlayer");
const leaderboardEl = document.getElementById("leaderboard");

playerNameInput.value = state.playerName;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API fejl: ${res.status}`);
  return res.json();
}

function renderStats(player) {
  xpEl.textContent = player.xp;
  levelEl.textContent = player.level;
  streakEl.textContent = player.streak;
}

async function ensurePlayer() {
  const raw = playerNameInput.value.trim() || "Spiller";
  state.playerName = raw;
  localStorage.setItem("laerquest_player", raw);
  const player = await api("/api/players", {
    method: "POST",
    body: JSON.stringify({ name: raw }),
  });
  renderStats(player);
  await loadLeaderboard();
}

async function loadSubjects() {
  const subjects = await api("/api/subjects");
  subjectsEl.innerHTML = "";
  subjects.forEach((subject) => {
    const clone = template.content.cloneNode(true);
    clone.querySelector("h3").textContent = subject.name;
    clone.querySelector(".desc").textContent = `${subject.description} • ${subject.missionCount} missioner`;
    clone.querySelector("button").addEventListener("click", () => startSubject(subject));
    subjectsEl.appendChild(clone);
  });
}

async function startSubject(subject) {
  if (!state.playerName) await ensurePlayer();
  state.currentSubject = subject;
  state.questionIndex = 0;
  state.questions = await api(`/api/subjects/${subject.id}/quiz`);
  gameTitle.textContent = `Bane: ${subject.name}`;
  lessonVideo.src = subject.video;
  gameSection.classList.remove("hidden");
  renderQuestion();
  feedback.textContent = "Se videoen og løs missionerne.";
}

function renderQuestion() {
  const question = state.questions[state.questionIndex];
  state.answeredCurrent = false;
  quiz.innerHTML = `
    <h3>Mission ${state.questionIndex + 1}</h3>
    <p>${question.q}</p>
    <div class="quiz-options">
      ${question.options.map((o, i) => `<button data-index="${i}">${String.fromCharCode(65 + i)}. ${o}</button>`).join("")}
    </div>
  `;

  quiz.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => answer(question.id, btn, Number(btn.dataset.index)));
  });
}

async function answer(questionId, button, selectedIndex) {
  if (state.answeredCurrent) return;
  state.answeredCurrent = true;

  const result = await api("/api/answer", {
    method: "POST",
    body: JSON.stringify({ playerName: state.playerName, questionId, selectedIndex }),
  });

  quiz.querySelectorAll("button").forEach((btn) => {
    const idx = Number(btn.dataset.index);
    if (idx === result.correctIndex) btn.classList.add("correct");
    if (btn === button && !result.correct) btn.classList.add("wrong");
    btn.disabled = true;
  });

  feedback.textContent = result.correct ? "Korrekt! +25 XP" : "Forkert svar – prøv næste mission";
  renderStats(result.player);
  await loadLeaderboard();
}

function nextQuestion() {
  if (!state.questions.length) return;
  if (state.questionIndex >= state.questions.length - 1) {
    feedback.textContent = "Bane færdig! Vælg en ny bane.";
    return;
  }
  state.questionIndex += 1;
  renderQuestion();
}

async function loadLeaderboard() {
  const board = await api("/api/leaderboard");
  leaderboardEl.innerHTML = board.length
    ? board.map((p) => `<li>${p.name} — ${p.xp} XP (Lv ${p.level})</li>`).join("")
    : "<li>Ingen spillere endnu</li>";
}

savePlayerBtn.addEventListener("click", ensurePlayer);
nextQuestionBtn.addEventListener("click", nextQuestion);
closeGameBtn.addEventListener("click", () => {
  gameSection.classList.add("hidden");
  lessonVideo.src = "";
});

(async function init() {
  await loadSubjects();
  if (state.playerName) {
    await ensurePlayer();
  } else {
    renderStats({ xp: 0, level: 1, streak: 0 });
    await loadLeaderboard();
  }
})();
