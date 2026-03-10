import { initializeApp } from "https://www.gstatic.com/firebasejs/12.10.0/firebase-app.js";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from "https://www.gstatic.com/firebasejs/12.10.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyAAV3AMIbAMePWBCt1PJ5xAPq-vG_v2d-s",
  authDomain: "missionary-lunch-calendar.firebaseapp.com",
  projectId: "missionary-lunch-calendar",
  storageBucket: "missionary-lunch-calendar.firebasestorage.app",
  messagingSenderId: "1037425270789",
  appId: "1:1037425270789:web:ea7b3183e1241036ebbc6c",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const EXPORT_DAYS_PT = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"];
const loginView = document.getElementById("loginView");
const calendarView = document.getElementById("calendarView");
const googleLoginBtn = document.getElementById("googleLoginBtn");
const loginStatusEl = document.getElementById("loginStatus");
const signOutBtn = document.getElementById("signOutBtn");
const headerRow = document.getElementById("headerRow");
const calendarBody = document.getElementById("calendarBody");
const monthPicker = document.getElementById("monthPicker");
const statusEl = document.getElementById("status");
const statusTextEl = document.getElementById("statusText");
const downloadBtn = document.getElementById("downloadBtn");
const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const wardInput = document.getElementById("wardInput");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const cancelSettingsBtn = document.getElementById("cancelSettingsBtn");
const statusSpinner = document.getElementById("statusSpinner");
const loginSpinner = document.getElementById("loginSpinner");
const googleIcon = document.getElementById("googleIcon");
const loginBtnText = document.getElementById("loginBtnText");
const pdayOverrides = {};
const mutedDaysByWeek = {};
let isCalendarInitialized = false;
let currentWard = "";
let currentProfile = 1;
let settingsEditProfile = 1;
let allSettings = {};

const calendarTitleEl = document.getElementById("calendarTitle");
const calendarSubtitleEl = document.getElementById("calendarSubtitle");
const slotTitleInput = document.getElementById("slotTitleInput");
const slotSubtitleInput = document.getElementById("slotSubtitleInput");

const DEFAULT_TITLES = [
  "Calendário de Almoço Missionário",
  "Calendário de Ajuda Missionária",
];
const DEFAULT_SUBTITLES = [
  "Adicione o nome das famílias nos dias da semana em que elas oferecem almoço aos Missionários",
  "Gerencie a agenda de ajuda aos Missionários",
];

function getProfileTitle(profile) {
  return allSettings[`slot_${profile}_title`] || DEFAULT_TITLES[profile - 1] || `Perfil ${profile}`;
}

function getProfileSubtitle(profile) {
  return allSettings[`slot_${profile}_subtitle`] || DEFAULT_SUBTITLES[profile - 1] || "";
}

function updateHeaderText() {
  calendarTitleEl.textContent = getProfileTitle(currentProfile);
  calendarSubtitleEl.textContent = getProfileSubtitle(currentProfile);
}

function updateTopbarSlotButtons() {
  document.querySelectorAll("#topbarSlotSwitcher .slot-btn").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.profile) === currentProfile);
  });
}

function updateSettingsSlotButtons() {
  document.querySelectorAll(".modal-slot-switcher .slot-btn").forEach((btn) => {
    btn.classList.toggle("active", Number(btn.dataset.settingsProfile) === settingsEditProfile);
  });
}

function populateSettingsSlotFields() {
  slotTitleInput.value = allSettings[`slot_${settingsEditProfile}_title`] || "";
  slotSubtitleInput.value = allSettings[`slot_${settingsEditProfile}_subtitle`] || "";
}

function getAuthenticatedUserId() {
  const currentUser = auth.currentUser;
  if (!currentUser || !currentUser.uid) {
    return "";
  }
  return currentUser.uid;
}

function showStatus(message, isError = false) {
  statusTextEl.textContent = message;
  statusEl.style.color = isError ? "#b42c2c" : "#6b7a90";
}

function setStatusLoading(message) {
  statusSpinner.classList.remove("hidden");
  showStatus(message);
}

function clearStatusLoading() {
  statusSpinner.classList.add("hidden");
}

function setDefaultMonth() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  monthPicker.value = `${year}-${month}`;
}

function renderHeader() {
  headerRow.innerHTML = "";
  const weekTh = document.createElement("th");
  weekTh.className = "week-head";
  weekTh.textContent = "Sem";
  headerRow.appendChild(weekTh);

  for (const day of EXPORT_DAYS_PT) {
    const th = document.createElement("th");
    th.textContent = day;
    headerRow.appendChild(th);
  }
}

async function saveCell(occurrence, dayOfWeek, slot, nameValue) {
  const userId = getAuthenticatedUserId();
  if (!userId) {
    showStatus("Você precisa estar logado para salvar", true);
    return;
  }

  setStatusLoading("Salvando...");
  try {
    const response = await fetch("/api/calendar", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": userId,
      },
      body: JSON.stringify({
        occurrence: occurrence,
        day_of_week: dayOfWeek,
        slot: slot,
        name: nameValue,
        profile: currentProfile,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      showStatus(data.error || "Erro ao salvar", true);
      return;
    }

    showStatus(`Salvo: ${EXPORT_DAYS_PT[DAYS.indexOf(dayOfWeek)] ?? dayOfWeek}, ocorrência ${occurrence}, slot ${slot} – "${nameValue || ""}"`);
  } catch (error) {
    showStatus("Erro de rede ao salvar", true);
  } finally {
    clearStatusLoading();
  }
}

function ordinalSuffix(value) {
  if (value % 100 >= 11 && value % 100 <= 13) return "th";
  if (value % 10 === 1) return "st";
  if (value % 10 === 2) return "nd";
  if (value % 10 === 3) return "rd";
  return "th";
}

function setPdayOverride(weekNumber, dayOfWeek) {
  const mutedDays = mutedDaysByWeek[weekNumber] || {};
  if (mutedDays[dayOfWeek]) {
    return;
  }

  if (dayOfWeek === "Monday") {
    delete pdayOverrides[weekNumber];
  } else {
    pdayOverrides[weekNumber] = dayOfWeek;
  }
  applyPdayOverridesView();
}

function toggleMuteDay(weekNumber, dayOfWeek) {
  if (!mutedDaysByWeek[weekNumber]) {
    mutedDaysByWeek[weekNumber] = {};
  }
  mutedDaysByWeek[weekNumber][dayOfWeek] = !mutedDaysByWeek[weekNumber][dayOfWeek];
  if (!mutedDaysByWeek[weekNumber][dayOfWeek]) {
    delete mutedDaysByWeek[weekNumber][dayOfWeek];
  }
  if (Object.keys(mutedDaysByWeek[weekNumber]).length === 0) {
    delete mutedDaysByWeek[weekNumber];
  }
  if (mutedDaysByWeek[weekNumber]?.[dayOfWeek] && pdayOverrides[weekNumber] === dayOfWeek) {
    delete pdayOverrides[weekNumber];
  }
  applyPdayOverridesView();
}

function applyPdayOverridesView() {
  const rows = Array.from(calendarBody.querySelectorAll("tr"));
  for (const row of rows) {
    const weekNumber = Number(row.dataset.weekNumber || "0");
    const hasOverride = Boolean(pdayOverrides[weekNumber]);
    const activeDay = pdayOverrides[weekNumber] || "Monday";
    const mutedDays = mutedDaysByWeek[weekNumber] || {};
    const dayCells = Array.from(row.querySelectorAll("td")).slice(1);
    let movedNames = ["", ""];
    if (activeDay !== "Monday") {
      const targetCell = dayCells.find((cell) => cell.dataset.dayOfWeek === activeDay);
      if (targetCell) {
        const targetInputs = Array.from(targetCell.querySelectorAll("input"));
        movedNames = [
          targetInputs[0] ? targetInputs[0].value.trim() : "",
          targetInputs[1] ? targetInputs[1].value.trim() : "",
        ];
      }
    }

    for (const cell of dayCells) {
      const dayOfWeek = cell.dataset.dayOfWeek;
      const box = cell.querySelector(".cell");
      if (!box) continue;
      const isMuted = Boolean(mutedDays[dayOfWeek]);
      if (hasOverride && dayOfWeek === activeDay) {
        box.classList.add("pday-active");
      } else {
        box.classList.remove("pday-active");
      }
      if (isMuted) {
        box.classList.add("muted-active");
      } else {
        box.classList.remove("muted-active");
      }

      const inputs = Array.from(cell.querySelectorAll("input"));
      for (const input of inputs) {
        input.disabled = isMuted;
      }
      const pdayBtn = cell.querySelector(".pday-toggle");
      if (pdayBtn) {
        pdayBtn.disabled = isMuted;
      }

      if (dayOfWeek === "Monday") {
        const mondayFixed = box.querySelector(".fixed-name");
        const mondayPreview = box.querySelector(".monday-preview");
        if (mondayFixed && mondayPreview) {
          if (activeDay === "Monday") {
            mondayFixed.style.display = "block";
            mondayPreview.style.display = "none";
            mondayPreview.textContent = "";
          } else {
            const previewText = movedNames.filter(Boolean).join(" / ");
            mondayFixed.style.display = "none";
            mondayPreview.textContent = previewText;
            mondayPreview.style.display = previewText ? "block" : "none";
          }
        }
      }
    }
  }
}

function renderCalendar(weeks) {
  calendarBody.innerHTML = "";

  for (const week of weeks) {
    const row = document.createElement("tr");
    row.dataset.weekNumber = String(week.week_number);
    const weekCell = document.createElement("td");
    weekCell.className = "week-cell";
    weekCell.textContent = `W${week.week_number}`;
    row.appendChild(weekCell);

    for (const cellData of week.cells) {
      const cell = document.createElement("td");
      cell.dataset.dayOfWeek = cellData.day_of_week;
      const box = document.createElement("div");
      box.className = "cell";

      const meta = document.createElement("div");
      meta.className = "meta";

      const dayNumber = document.createElement("span");
      dayNumber.textContent = cellData.day_number === null ? "-" : String(cellData.day_number);

      meta.appendChild(dayNumber);

      if (cellData.day_number !== null) {
        const actions = document.createElement("div");
        actions.className = "meta-actions";

        const pdayToggle = document.createElement("button");
        pdayToggle.type = "button";
        pdayToggle.className = "pday-toggle";
        pdayToggle.textContent = "P";
        pdayToggle.title = "Definir PDAY para esta semana";
        pdayToggle.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          setPdayOverride(week.week_number, cellData.day_of_week);
        });
        actions.appendChild(pdayToggle);

        const muteToggle = document.createElement("button");
        muteToggle.type = "button";
        muteToggle.className = "mute-toggle";
        muteToggle.textContent = "M";
        muteToggle.title = "Silenciar este dia para exportação";
        muteToggle.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          toggleMuteDay(week.week_number, cellData.day_of_week);
        });
        actions.appendChild(muteToggle);

        meta.prepend(actions);
      }
      box.appendChild(meta);

      if (cellData.day_of_week === "Monday") {
        const fixedName = document.createElement("div");
        fixedName.className = "fixed-name";
        fixedName.textContent = "PDAY";
        box.appendChild(fixedName);

        const mondayPreview = document.createElement("div");
        mondayPreview.className = "monday-preview";
        box.appendChild(mondayPreview);
      } else if (cellData.day_number === null) {
        const empty = document.createElement("div");
        empty.className = "empty-day";
        empty.textContent = "Sem data neste mês";
        box.appendChild(empty);
      } else {
        const pdayLabel = document.createElement("div");
        pdayLabel.className = "fixed-name pday-label";
        pdayLabel.textContent = "PDAY";
        box.appendChild(pdayLabel);

        const editableContent = document.createElement("div");
        editableContent.className = "editable-content";
        const firstValue = (cellData.names && cellData.names.first) || cellData.name || "";
        const secondValue = (cellData.names && cellData.names.second) || "";
        for (let slot = 1; slot <= 2; slot += 1) {
          const input = document.createElement("input");
          input.className = slot === 2 ? "name-input secondary" : "name-input";
          input.type = "text";
          input.value = slot === 1 ? firstValue : secondValue;
          input.placeholder = `Digite um nome (${slot})`;
          input.addEventListener("change", () => {
            if (cellData.occurrence) {
              saveCell(cellData.occurrence, cellData.day_of_week, slot, input.value.trim());
            }
            applyPdayOverridesView();
          });
          editableContent.appendChild(input);
        }
        box.appendChild(editableContent);
      }

      cell.appendChild(box);
      row.appendChild(cell);
    }

    calendarBody.appendChild(row);
  }
  applyPdayOverridesView();
}

async function fetchCalendar() {
  if (!monthPicker.value) {
    return;
  }
  const userId = getAuthenticatedUserId();
  if (!userId) {
    showStatus("Você precisa estar logado para carregar o calendário", true);
    return;
  }

  const [yearStr, monthStr] = monthPicker.value.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);

  monthPicker.disabled = true;
  setStatusLoading("Carregando...");
  try {
    const response = await fetch(`/api/calendar?year=${year}&month=${month}&profile=${currentProfile}`, {
      headers: { "X-User-Id": userId },
    });
    const data = await response.json();

    if (!response.ok) {
      showStatus(data.error || "Erro ao carregar calendário", true);
      return;
    }

    Object.keys(pdayOverrides).forEach((key) => delete pdayOverrides[key]);
    Object.keys(mutedDaysByWeek).forEach((key) => delete mutedDaysByWeek[key]);
    renderCalendar(data.weeks);
    showStatus(`Exibindo ${String(month).padStart(2, "0")}/${year}`);
  } catch (error) {
    showStatus("Erro de rede ao carregar calendário", true);
  } finally {
    monthPicker.disabled = false;
    clearStatusLoading();
  }
}

function collectCalendarSnapshot() {
  const weeks = [];
  const rows = Array.from(calendarBody.querySelectorAll("tr"));

  for (const row of rows) {
    const weekCell = row.querySelector(".week-cell");
    const weekLabel = weekCell ? weekCell.textContent.trim() : "";
    const dayCells = Array.from(row.querySelectorAll("td")).slice(1);
    const cells = dayCells.map((cell) => {
      const dayNumberEl = cell.querySelector(".meta span");
      const fixedNameEl = cell.querySelector(".fixed-name");
      const inputEls = Array.from(cell.querySelectorAll("input"));
      const dayNumber = dayNumberEl ? dayNumberEl.textContent.trim() : "-";
      let names = ["", ""];
      if (inputEls.length > 0) {
        names = [
          inputEls[0] ? inputEls[0].value.trim() : "",
          inputEls[1] ? inputEls[1].value.trim() : "",
        ];
      } else if (fixedNameEl) {
        names = [fixedNameEl.textContent.trim(), ""];
      }
      return { dayNumber, names };
    });

    weeks.push({ weekLabel, cells });
  }

  return weeks;
}

function downloadCalendarImage() {
  const weeks = collectCalendarSnapshot();
  const exportSourceWeeks = weeks.map((week) => ({
    weekLabel: week.weekLabel,
    cells: week.cells.map((cell) => ({ dayNumber: cell.dayNumber, names: [...cell.names] })),
  }));

  for (let w = 0; w < exportSourceWeeks.length; w += 1) {
    const weekNumber = w + 1;
    const mutedDays = mutedDaysByWeek[weekNumber] || {};
    for (let d = 0; d < DAYS.length; d += 1) {
      if (mutedDays[DAYS[d]]) {
        exportSourceWeeks[w].cells[d].names = ["", ""];
      }
    }
  }

  for (let w = 0; w < exportSourceWeeks.length; w += 1) {
    const weekNumber = w + 1;
    const targetDay = pdayOverrides[weekNumber];
    if (!targetDay || targetDay === "Monday") {
      continue;
    }

    const targetDayIndex = DAYS.indexOf(targetDay);
    if (targetDayIndex < 0) {
      continue;
    }

    const mondayCell = exportSourceWeeks[w].cells[0];
    const targetCell = exportSourceWeeks[w].cells[targetDayIndex];
    if (!targetCell || targetCell.dayNumber === "-") {
      continue;
    }

    mondayCell.names = [...(targetCell.names || ["", ""])];
    targetCell.names = ["PDAY", ""];
  }

  for (let w = 0; w < exportSourceWeeks.length; w += 1) {
    const weekNumber = w + 1;
    const targetDay = pdayOverrides[weekNumber] || "Monday";
    const mutedDays = mutedDaysByWeek[weekNumber] || {};
    for (let d = 0; d < DAYS.length; d += 1) {
      const dayName = DAYS[d];
      if (mutedDays[dayName] && dayName !== targetDay) {
        exportSourceWeeks[w].cells[d].names = ["", ""];
      }
    }
  }
  const exportWeeks = [...exportSourceWeeks];
  while (exportWeeks.length > 1) {
    const lastWeek = exportWeeks[exportWeeks.length - 1];
    const hasAnyDate = lastWeek.cells.some((cell) => cell.dayNumber && cell.dayNumber !== "-");
    if (hasAnyDate) {
      break;
    }
    exportWeeks.pop();
  }

  const weekCount = exportWeeks.length || 1;
  const selected = monthPicker.value || "calendar";
  const [y, m] = selected.split("-");
  const profileTitle = getProfileTitle(currentProfile);
  const title = y && m ? `${m}/${y}` : profileTitle;
  const dateStamp = new Date().toISOString().slice(0, 10);

  const dayColW = 152;
  const headerH = 44;
  const rowH = 104;
  const pad = 16;
  const width = pad * 2 + dayColW * 7;
  const height = pad * 2 + headerH + rowH * weekCount + 52;
  const scale = 2;

  const canvas = document.createElement("canvas");
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);

  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "#1a2433";
  ctx.font = "bold 18px Segoe UI, Tahoma, sans-serif";
  ctx.fillText(`${profileTitle} ${title}`, pad, pad + 4);

  const gridX = pad;
  const gridY = pad + 16;
  const gridW = dayColW * 7;
  const gridH = headerH + rowH * weekCount;

  ctx.fillStyle = "#eff4fa";
  ctx.fillRect(gridX, gridY, gridW, headerH);
  ctx.strokeStyle = "#d4dde8";
  ctx.lineWidth = 1;

  ctx.beginPath();
  for (let i = 0; i <= weekCount; i += 1) {
    const yLine = gridY + headerH + i * rowH;
    ctx.moveTo(gridX, yLine);
    ctx.lineTo(gridX + gridW, yLine);
  }
  for (let i = 0; i <= 7; i += 1) {
    const xLine = gridX + i * dayColW;
    ctx.moveTo(xLine, gridY);
    ctx.lineTo(xLine, gridY + gridH);
  }
  ctx.stroke();

  ctx.fillStyle = "#44556d";
  ctx.font = "bold 13px Segoe UI, Tahoma, sans-serif";
  ctx.textBaseline = "middle";
  for (let i = 0; i < EXPORT_DAYS_PT.length; i += 1) {
    const x = gridX + i * dayColW + dayColW / 2;
    ctx.textAlign = "center";
    ctx.fillText(EXPORT_DAYS_PT[i], x, gridY + headerH / 2);
  }

  for (let w = 0; w < exportWeeks.length; w += 1) {
    const rowTop = gridY + headerH + w * rowH;

    for (let d = 0; d < DAYS.length; d += 1) {
      const cell = exportWeeks[w].cells[d] || { dayNumber: "-", names: ["", ""] };
      const left = gridX + d * dayColW;
      const centerX = left + dayColW / 2;
      const centerY = rowTop + rowH / 2;

      ctx.fillStyle = "#6b7a90";
      ctx.font = "12px Segoe UI, Tahoma, sans-serif";
      ctx.textAlign = "right";
      ctx.fillText(cell.dayNumber || "-", left + dayColW - 10, rowTop + 14);

      const firstName = (cell.names && cell.names[0]) || "";
      const secondName = (cell.names && cell.names[1]) || "";
      const hasFirst = Boolean(firstName);
      const hasSecond = Boolean(secondName);

      ctx.textAlign = "center";
      if (firstName === "PDAY") {
        ctx.fillStyle = "#0f7b6c";
        ctx.font = "bold 20px Segoe UI, Tahoma, sans-serif";
        ctx.fillText(firstName, centerX, centerY);
      } else if (hasFirst && hasSecond) {
        ctx.fillStyle = "#138c3f";
        ctx.font = "bold 18px Segoe UI, Tahoma, sans-serif";
        ctx.fillText(firstName, centerX, centerY - 12);
        ctx.fillStyle = "#d6a800";
        ctx.fillText(secondName, centerX, centerY + 12);
      } else {
        const singleName = hasFirst ? firstName : secondName;
        ctx.fillStyle = "#1a2433";
        ctx.font = "bold 20px Segoe UI, Tahoma, sans-serif";
        ctx.fillText(singleName, centerX, centerY);
      }
    }
  }

  const legendY = gridY + gridH + 24;
  const squareSize = 12;
  const legendStartX = gridX + 10;
  const ward = currentWard || "Ala";

  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#138c3f";
  ctx.fillRect(legendStartX, legendY - squareSize / 2, squareSize, squareSize);
  ctx.fillStyle = "#1a2433";
  ctx.font = "bold 14px Segoe UI, Tahoma, sans-serif";
  ctx.fillText(`${ward} A`, legendStartX + squareSize + 8, legendY);

  const secondLegendX = legendStartX + 150;
  ctx.fillStyle = "#d6a800";
  ctx.fillRect(secondLegendX, legendY - squareSize / 2, squareSize, squareSize);
  ctx.fillStyle = "#1a2433";
  ctx.fillText(`${ward} B`, secondLegendX + squareSize + 8, legendY);

  const link = document.createElement("a");
  link.href = canvas.toDataURL("image/png");
  link.download = `calendar-${dateStamp}.png`;
  link.click();
  showStatus(`Baixado: calendar-${dateStamp}.png`);
}

async function loadSettings() {
  const userId = getAuthenticatedUserId();
  if (!userId) return;
  setStatusLoading("Carregando...");
  try {
    const resp = await fetch("/api/settings", { headers: { "X-User-Id": userId } });
    if (resp.ok) {
      const data = await resp.json();
      allSettings = data.settings || {};
      currentWard = allSettings.ward || "";
      wardInput.value = currentWard;
      updateHeaderText();
    }
  } catch (err) {
    console.warn("Falha ao carregar configurações:", err);
  } finally {
    clearStatusLoading();
  }
}

async function persistSettings() {
  const userId = getAuthenticatedUserId();
  if (!userId) return;
  const ward = wardInput.value.trim();
  saveSettingsBtn.disabled = true;
  try {
    const body = {
      ward,
      [`slot_${settingsEditProfile}_title`]: slotTitleInput.value.trim(),
      [`slot_${settingsEditProfile}_subtitle`]: slotSubtitleInput.value.trim(),
    };
    const resp = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-User-Id": userId },
      body: JSON.stringify(body),
    });
    if (resp.ok) {
      const data = await resp.json();
      allSettings = data.settings || {};
      currentWard = allSettings.ward || "";
      settingsModal.classList.add("hidden");
      updateHeaderText();
      showStatus("Configurações salvas");
    } else {
      showStatus("Erro ao salvar configurações", true);
    }
  } catch (_) {
    showStatus("Erro ao salvar configurações", true);
  } finally {
    saveSettingsBtn.disabled = false;
  }
}

monthPicker.addEventListener("change", fetchCalendar);
downloadBtn.addEventListener("click", downloadCalendarImage);
settingsBtn.addEventListener("click", () => {
  wardInput.value = currentWard;
  settingsEditProfile = currentProfile;
  updateSettingsSlotButtons();
  populateSettingsSlotFields();
  settingsModal.classList.remove("hidden");
});
saveSettingsBtn.addEventListener("click", persistSettings);
cancelSettingsBtn.addEventListener("click", () => settingsModal.classList.add("hidden"));
settingsModal.addEventListener("click", (e) => {
  if (e.target === settingsModal) settingsModal.classList.add("hidden");
});

document.querySelectorAll("#topbarSlotSwitcher .slot-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const profile = Number(btn.dataset.profile);
    if (profile === currentProfile) return;
    currentProfile = profile;
    updateTopbarSlotButtons();
    updateHeaderText();
    Object.keys(pdayOverrides).forEach((k) => delete pdayOverrides[k]);
    Object.keys(mutedDaysByWeek).forEach((k) => delete mutedDaysByWeek[k]);
    fetchCalendar();
  });
});

document.querySelectorAll(".modal-slot-switcher .slot-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    settingsEditProfile = Number(btn.dataset.settingsProfile);
    updateSettingsSlotButtons();
    populateSettingsSlotFields();
  });
});
googleLoginBtn.addEventListener("click", async () => {
  loginStatusEl.textContent = "";
  try {
    await signInWithPopup(auth, googleProvider);
  } catch (error) {
    loginStatusEl.textContent = "Falha no login com Google. Tente novamente.";
  }
});
signOutBtn.addEventListener("click", async () => {
  await signOut(auth);
});

onAuthStateChanged(auth, (user) => {
  if (!user) {
    calendarView.classList.add("hidden");
    loginView.classList.remove("hidden");
    loginStatusEl.textContent = "";
    loginSpinner.classList.add("hidden");
    googleIcon.style.display = "";
    loginBtnText.textContent = "Entrar com Google";
    googleLoginBtn.disabled = false;
    currentWard = "";
    return;
  }

  loginView.classList.add("hidden");
  calendarView.classList.remove("hidden");
  if (!isCalendarInitialized) {
    renderHeader();
    setDefaultMonth();
    isCalendarInitialized = true;
  }
  loadSettings();
  fetchCalendar();
});
