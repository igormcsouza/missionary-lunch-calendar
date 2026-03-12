import { initializeApp } from "https://www.gstatic.com/firebasejs/12.10.0/firebase-app.js";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from "https://www.gstatic.com/firebasejs/12.10.0/firebase-auth.js";

const firebaseConfig = {
  apiKey: "AIzaSyAQHtKCPY2ns3ohmp3D1s6dFfTx4Wc2SNI",
  authDomain: "mission-leader-assistant.firebaseapp.com",
  projectId: "mission-leader-assistant",
  storageBucket: "mission-leader-assistant.firebasestorage.app",
  messagingSenderId: "754740691680",
  appId: "1:754740691680:web:f246612a5726d37162c685",
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
const menuToggleBtn = document.getElementById("menuToggleBtn");
const sideDrawer = document.getElementById("sideDrawer");
const drawerBackdrop = document.getElementById("drawerBackdrop");
const drawerSignOutBtn = document.getElementById("drawerSignOutBtn");
const drawerUserPhoto = document.getElementById("drawerUserPhoto");
const drawerUserName = document.getElementById("drawerUserName");
const pdayOverrides = {};
const mutedDaysByWeek = {};
let isCalendarInitialized = false;
let currentWard = "";
let currentProfile = 1;
let settingsEditProfile = 1;
let allSettings = {};

const NAV_ICONS = {
  calendar: `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.8" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="4" width="18" height="18" rx="2.5"></rect>
    <line x1="3" y1="9" x2="21" y2="9"></line>
    <line x1="8" y1="2" x2="8" y2="6"></line>
    <line x1="16" y1="2" x2="16" y2="6"></line>
  </svg>`,
  baptismalPlan: `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke-width="1.8" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C8.68 2 6 4.68 6 8c0 4.5 4.5 10 6 11.8C13.5 18 18 12.5 18 8c0-3.32-2.68-6-6-6z"></path>
    <circle cx="12" cy="8" r="2.5"></circle>
  </svg>`,
};

let currentRoute = "/calendar";

const navigationItems = [
  {
    id: "calendar",
    label: "Calendário",
    icon: NAV_ICONS.calendar,
    route: "/calendar",
  },
  {
    id: "baptismal-plan",
    label: "Planejamento Batismal",
    icon: NAV_ICONS.baptismalPlan,
    route: "/baptismal-plan",
  },
];

const baptismalPlanView = document.getElementById("baptismalPlanView");

function navigateTo(route) {
  currentRoute = route;
  if (route === "/calendar") {
    calendarView.classList.remove("hidden");
    baptismalPlanView.classList.add("hidden");
  } else if (route === "/baptismal-plan") {
    calendarView.classList.add("hidden");
    baptismalPlanView.classList.remove("hidden");
    initBaptismalPlanView();
  }
  // Update active nav item
  const navList = sideDrawer.querySelector(".nav-items");
  navList.querySelectorAll(".nav-item").forEach((li) => {
    li.classList.toggle("active", li.dataset.route === route);
  });
}

function buildNavItems() {
  const navList = sideDrawer.querySelector(".nav-items");
  navList.innerHTML = "";
  for (const item of navigationItems) {
    const li = document.createElement("li");
    li.className = "nav-item" + (item.route === currentRoute ? " active" : "");
    li.dataset.route = item.route;
    li.setAttribute("role", "listitem");
    li.innerHTML = `${item.icon}<span>${item.label}</span>`;
    li.addEventListener("click", () => {
      navigateTo(item.route);
      closeDrawer();
    });
    navList.appendChild(li);
  }
}

function openDrawer() {
  sideDrawer.classList.add("open");
  drawerBackdrop.classList.remove("hidden");
  menuToggleBtn.setAttribute("aria-expanded", "true");
}

function closeDrawer() {
  sideDrawer.classList.remove("open");
  drawerBackdrop.classList.add("hidden");
  menuToggleBtn.setAttribute("aria-expanded", "false");
}

function toggleDrawer() {
  if (sideDrawer.classList.contains("open")) {
    closeDrawer();
  } else {
    openDrawer();
  }
}

function updateDrawerUser(user) {
  if (user) {
    drawerUserName.textContent = user.displayName || user.email || "Usuário";
    if (user.photoURL) {
      drawerUserPhoto.src = user.photoURL;
      drawerUserPhoto.style.display = "";
    } else {
      drawerUserPhoto.src = "";
      drawerUserPhoto.style.display = "none";
    }
  } else {
    drawerUserName.textContent = "Usuário";
    drawerUserPhoto.src = "";
    drawerUserPhoto.style.display = "none";
  }
}

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
menuToggleBtn.addEventListener("click", toggleDrawer);
drawerBackdrop.addEventListener("click", closeDrawer);
drawerSignOutBtn.addEventListener("click", async () => {
  closeDrawer();
  await signOut(auth);
});

buildNavItems();

// ── Baptismal Plan ────────────────────────────────────────────────────────

const bpPlanList = document.getElementById("bpPlanList");
const bpEmptyState = document.getElementById("bpEmptyState");
const bpEditorContent = document.getElementById("bpEditorContent");
const bpNewPlanBtn = document.getElementById("bpNewPlanBtn");
const bpExportPdfBtn = document.getElementById("bpExportPdfBtn");
const bpSaveStatus = document.getElementById("bpSaveStatus");
const bpServiceDate = document.getElementById("bpServiceDate");
const bpServiceTime = document.getElementById("bpServiceTime");
const bpWard = document.getElementById("bpWard");
const bpLocation = document.getElementById("bpLocation");
const bpConductingLeader = document.getElementById("bpConductingLeader");
const bpStatus = document.getElementById("bpStatus");
const bpAddCandidateBtn = document.getElementById("bpAddCandidateBtn");
const bpCandidatesList = document.getElementById("bpCandidatesList");
const bpOrdinancesList = document.getElementById("bpOrdinancesList");
const bpOrdinancesEmpty = document.getElementById("bpOrdinancesEmpty");
const bpWitnessesList = document.getElementById("bpWitnessesList");
const bpWitnessesEmpty = document.getElementById("bpWitnessesEmpty");
const bpProgramList = document.getElementById("bpProgramList");
const bpNotes = document.getElementById("bpNotes");

let bpCurrentPlanId = null;
let bpCurrentPlan = null;
let bpPlanSummaries = [];
let bpViewInitialized = false;
let bpEditorReady = false;

const BP_STATUS_PT = {
  Draft: "Rascunho",
  Scheduled: "Agendado",
  Completed: "Realizado",
  Archived: "Arquivado",
};

const BP_CANDIDATE_TYPE_PT = {
  ChildOfRecord: "Filho de Registro",
  Convert: "Converso",
};

const BP_PRIESTHOOD_PT = {
  Priest: "Sacerdote",
  "Melchizedek Priesthood": "Sacerdócio de Melquisedeque",
};

function bpFormatDate(dateStr) {
  if (!dateStr) return "Sem data";
  const [year, month, day] = dateStr.split("-");
  if (!year || !month || !day) return dateStr;
  const months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                  "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
  return `${parseInt(day, 10)} ${months[parseInt(month, 10) - 1]} ${year}`;
}

function bpStatusClass(status) {
  const map = { Scheduled: "status-scheduled", Completed: "status-completed", Archived: "status-archived" };
  return map[status] || "";
}

// ── API ───────────────────────────────────────────────────────────────────

function bpGetHeaders() {
  const user = auth.currentUser;
  return user ? { "X-User-Id": user.uid, "Content-Type": "application/json" } : {};
}

async function bpFetchPlans() {
  const resp = await fetch("/api/baptismal-plans", { headers: bpGetHeaders() });
  if (!resp.ok) return [];
  const json = await resp.json();
  return json.plans || [];
}

async function bpFetchPlan(planId) {
  const resp = await fetch(`/api/baptismal-plans/${planId}`, { headers: bpGetHeaders() });
  if (!resp.ok) return null;
  const json = await resp.json();
  return json.plan || null;
}

async function bpCreatePlan() {
  const resp = await fetch("/api/baptismal-plans", {
    method: "POST",
    headers: bpGetHeaders(),
    body: JSON.stringify({}),
  });
  if (!resp.ok) return null;
  const json = await resp.json();
  return json.plan || null;
}

async function bpSavePlan(planId, planData) {
  const resp = await fetch(`/api/baptismal-plans/${planId}`, {
    method: "PUT",
    headers: bpGetHeaders(),
    body: JSON.stringify(planData),
  });
  if (!resp.ok) return null;
  const json = await resp.json();
  return json.plan || null;
}

// ── Render helpers ────────────────────────────────────────────────────────

function bpRenderPlanList(summaries) {
  bpPlanList.innerHTML = "";
  if (!summaries.length) {
    const li = document.createElement("li");
    li.className = "bp-plan-item";
    li.style.cursor = "default";
    li.innerHTML = `<p style="color:var(--subtle);font-size:0.85rem;margin:0">Nenhum planejamento</p>`;
    bpPlanList.appendChild(li);
    return;
  }
  for (const s of summaries) {
    const li = document.createElement("li");
    li.className = "bp-plan-item" + (s.id === bpCurrentPlanId ? " active" : "");
    li.dataset.planId = s.id;
    li.setAttribute("role", "listitem");
    const names = s.candidates && s.candidates.length
      ? s.candidates.map((n) => n || "Sem nome").join(", ")
      : "Sem candidatos";
    const statusPt = BP_STATUS_PT[s.status] || s.status;
    li.innerHTML = `
      <div class="bp-plan-item-date">${bpFormatDate(s.serviceDate)}</div>
      <div class="bp-plan-item-names">Batismo: ${names}</div>
      <span class="bp-plan-item-status ${bpStatusClass(s.status)}">${statusPt}</span>`;
    li.addEventListener("click", () => bpLoadPlan(s.id));
    bpPlanList.appendChild(li);
  }
}

function bpRenderCandidates(candidates) {
  bpCandidatesList.innerHTML = "";
  if (!candidates || !candidates.length) return;
  candidates.forEach((c, idx) => {
    const card = document.createElement("div");
    card.className = "bp-candidate-card";
    card.dataset.candidateId = c.id;
    card.innerHTML = `
      <div class="bp-candidate-card-header">
        <span class="bp-candidate-card-title">Candidato ${idx + 1}</span>
        <button class="bp-btn-danger bp-remove-candidate" type="button" data-cid="${c.id}">Remover</button>
      </div>
      <div class="bp-candidate-grid">
        <div class="bp-field">
          <label class="bp-label">Nome Completo</label>
          <input class="bp-input bp-c-fullName" type="text" value="${_esc(c.fullName)}" placeholder="Nome completo" />
        </div>
        <div class="bp-field">
          <label class="bp-label">Data de Nascimento</label>
          <input class="bp-input bp-c-birthDate" type="date" value="${_esc(c.birthDate)}" />
        </div>
        <div class="bp-field">
          <label class="bp-label">Idade</label>
          <input class="bp-input bp-c-age" type="text" value="${_esc(c.age)}" placeholder="Idade" />
        </div>
        <div class="bp-field">
          <label class="bp-label">Tipo</label>
          <select class="bp-select bp-c-candidateType">
            <option value="Convert" ${c.candidateType === "Convert" ? "selected" : ""}>Converso</option>
            <option value="ChildOfRecord" ${c.candidateType === "ChildOfRecord" ? "selected" : ""}>Filho de Registro</option>
          </select>
        </div>
        <div class="bp-field">
          <label class="bp-label">Entrevistado por</label>
          <input class="bp-input bp-c-interviewedBy" type="text" value="${_esc(c.interviewedBy)}" placeholder="Nome" />
        </div>
        <div class="bp-field bp-checkbox-field">
          <input class="bp-checkbox bp-c-interviewCompleted" id="bpIC_${c.id}" type="checkbox" ${c.interviewCompleted ? "checked" : ""} />
          <label class="bp-checkbox-label" for="bpIC_${c.id}">Entrevista Realizada</label>
        </div>
      </div>`;
    bpCandidatesList.appendChild(card);

    // blur / change auto-save on each field
    card.querySelectorAll(".bp-input, .bp-select, .bp-checkbox").forEach((el) => {
      const evt = el.type === "checkbox" ? "change" : "blur";
      el.addEventListener(evt, () => { if (bpEditorReady) bpAutoSave(); });
    });
    card.querySelector(".bp-remove-candidate").addEventListener("click", () => {
      bpRemoveCandidate(c.id);
    });
  });
}

function bpRenderOrdinances(candidates, ordinances) {
  bpOrdinancesList.innerHTML = "";
  if (!candidates || !candidates.length) {
    bpOrdinancesEmpty.classList.remove("hidden");
    return;
  }
  bpOrdinancesEmpty.classList.add("hidden");
  const ordMap = {};
  (ordinances || []).forEach((o) => { ordMap[o.candidateId] = o; });
  candidates.forEach((c) => {
    const o = ordMap[c.id] || {};
    const name = c.fullName || "Candidato";
    const card = document.createElement("div");
    card.className = "bp-ord-card";
    card.dataset.candidateId = c.id;
    card.innerHTML = `
      <div class="bp-ord-card-title">${_esc(name)}</div>
      <div class="bp-ord-grid">
        <div class="bp-field">
          <label class="bp-label">Batizado por</label>
          <input class="bp-input bp-o-baptizerName" type="text" value="${_esc(o.baptizerName || "")}" placeholder="Nome" />
        </div>
        <div class="bp-field">
          <label class="bp-label">Sacerdócio</label>
          <select class="bp-select bp-o-baptizerPriesthood">
            <option value="">Selecionar</option>
            <option value="Priest" ${o.baptizerPriesthood === "Priest" ? "selected" : ""}>Sacerdote</option>
            <option value="Melchizedek Priesthood" ${o.baptizerPriesthood === "Melchizedek Priesthood" ? "selected" : ""}>Sacerdócio de Melquisedeque</option>
          </select>
        </div>
        <div class="bp-field">
          <label class="bp-label">Confirmado por</label>
          <input class="bp-input bp-o-confirmationBy" type="text" value="${_esc(o.confirmationBy || "")}" placeholder="Nome" />
        </div>
      </div>`;
    bpOrdinancesList.appendChild(card);
    card.querySelectorAll(".bp-input, .bp-select").forEach((el) => {
      el.addEventListener("blur", () => { if (bpEditorReady) bpAutoSave(); });
      el.addEventListener("change", () => { if (bpEditorReady) bpAutoSave(); });
    });
  });
}

function bpRenderWitnesses(candidates, witnesses) {
  bpWitnessesList.innerHTML = "";
  if (!candidates || !candidates.length) {
    bpWitnessesEmpty.classList.remove("hidden");
    return;
  }
  bpWitnessesEmpty.classList.add("hidden");
  const witMap = {};
  (witnesses || []).forEach((w) => { witMap[w.candidateId] = w; });
  candidates.forEach((c) => {
    const w = witMap[c.id] || {};
    const name = c.fullName || "Candidato";
    const card = document.createElement("div");
    card.className = "bp-witness-card";
    card.dataset.candidateId = c.id;
    const w1 = w.witness1 || "";
    const w2 = w.witness2 || "";
    const warnHtml = (!w1 || !w2)
      ? `<p class="bp-warning">⚠ Mínimo de 2 testemunhas por batismo.</p>` : "";
    card.innerHTML = `
      <div class="bp-witness-card-title">${_esc(name)}</div>
      <div class="bp-witness-grid">
        <div class="bp-field">
          <label class="bp-label">Testemunha 1</label>
          <input class="bp-input bp-w-witness1" type="text" value="${_esc(w1)}" placeholder="Nome" />
        </div>
        <div class="bp-field">
          <label class="bp-label">Testemunha 2</label>
          <input class="bp-input bp-w-witness2" type="text" value="${_esc(w2)}" placeholder="Nome" />
        </div>
      </div>
      ${warnHtml}`;
    bpWitnessesList.appendChild(card);
    card.querySelectorAll(".bp-input").forEach((el) => {
      el.addEventListener("blur", () => { if (bpEditorReady) bpAutoSave(); });
    });
  });
}

function bpRenderProgram(program) {
  bpProgramList.innerHTML = "";
  (program || []).forEach((item, idx) => {
    const row = document.createElement("div");
    row.className = "bp-program-item";
    row.dataset.programIndex = idx;
    row.innerHTML = `
      <span class="bp-program-item-name">${_esc(item.item)}</span>
      <input class="bp-input bp-p-assignee" type="text" value="${_esc(item.assignee || "")}" placeholder="Responsável" />`;
    bpProgramList.appendChild(row);
    row.querySelector(".bp-p-assignee").addEventListener("blur", () => {
      if (bpEditorReady) bpAutoSave();
    });
  });
}

function bpRenderEditor(plan) {
  bpEditorReady = false;
  bpEmptyState.classList.add("hidden");
  bpEditorContent.classList.remove("hidden");

  bpServiceDate.value = plan.serviceDate || "";
  bpServiceTime.value = plan.serviceTime || "";
  bpWard.value = plan.ward || "";
  bpLocation.value = plan.location || "";
  bpConductingLeader.value = plan.conductingLeader || "";
  bpStatus.value = plan.status || "Draft";
  bpNotes.value = plan.notes || "";

  bpRenderCandidates(plan.candidates || []);
  bpRenderOrdinances(plan.candidates || [], plan.ordinances || []);
  bpRenderWitnesses(plan.candidates || [], plan.witnesses || []);
  bpRenderProgram(plan.program || []);

  bpEditorReady = true;
}

// ── Actions ───────────────────────────────────────────────────────────────

function _esc(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function bpCollectPlanData() {
  const candidates = [];
  bpCandidatesList.querySelectorAll(".bp-candidate-card").forEach((card) => {
    candidates.push({
      id: card.dataset.candidateId,
      fullName: card.querySelector(".bp-c-fullName").value,
      birthDate: card.querySelector(".bp-c-birthDate").value,
      age: card.querySelector(".bp-c-age").value,
      candidateType: card.querySelector(".bp-c-candidateType").value,
      interviewCompleted: card.querySelector(".bp-c-interviewCompleted").checked,
      interviewedBy: card.querySelector(".bp-c-interviewedBy").value,
    });
  });

  const ordinances = [];
  bpOrdinancesList.querySelectorAll(".bp-ord-card").forEach((card) => {
    ordinances.push({
      candidateId: card.dataset.candidateId,
      baptizerName: card.querySelector(".bp-o-baptizerName").value,
      baptizerPriesthood: card.querySelector(".bp-o-baptizerPriesthood").value,
      confirmationBy: card.querySelector(".bp-o-confirmationBy").value,
    });
  });

  const witnesses = [];
  bpWitnessesList.querySelectorAll(".bp-witness-card").forEach((card) => {
    witnesses.push({
      candidateId: card.dataset.candidateId,
      witness1: card.querySelector(".bp-w-witness1").value,
      witness2: card.querySelector(".bp-w-witness2").value,
    });
  });

  const program = [];
  bpProgramList.querySelectorAll(".bp-program-item").forEach((row) => {
    const assignee = row.querySelector(".bp-p-assignee").value;
    const itemName = row.querySelector(".bp-program-item-name").textContent;
    program.push({ item: itemName, assignee });
  });

  return {
    serviceDate: bpServiceDate.value,
    serviceTime: bpServiceTime.value,
    ward: bpWard.value,
    location: bpLocation.value,
    conductingLeader: bpConductingLeader.value,
    status: bpStatus.value,
    candidates,
    ordinances,
    witnesses,
    program,
    notes: bpNotes.value,
  };
}

async function bpAutoSave() {
  if (!bpCurrentPlanId) return;
  bpSaveStatus.textContent = "Salvando…";
  const data = bpCollectPlanData();
  const updated = await bpSavePlan(bpCurrentPlanId, data);
  if (updated) {
    bpCurrentPlan = updated;
    bpSaveStatus.textContent = "Salvo";
    // Refresh summary list entry
    const idx = bpPlanSummaries.findIndex((p) => p.id === bpCurrentPlanId);
    const summary = {
      id: updated.id,
      serviceDate: updated.serviceDate,
      candidates: (updated.candidates || []).map((c) => c.fullName || ""),
      status: updated.status,
    };
    if (idx >= 0) {
      bpPlanSummaries[idx] = summary;
    } else {
      bpPlanSummaries.unshift(summary);
    }
    bpRenderPlanList(bpPlanSummaries);
    setTimeout(() => { bpSaveStatus.textContent = ""; }, 2000);
  } else {
    bpSaveStatus.textContent = "Erro ao salvar";
  }
}

async function bpLoadPlan(planId) {
  bpEditorReady = false;
  const plan = await bpFetchPlan(planId);
  if (!plan) return;
  bpCurrentPlanId = planId;
  bpCurrentPlan = plan;
  bpRenderEditor(plan);
  bpRenderPlanList(bpPlanSummaries);
}

async function bpHandleNewPlan() {
  bpEditorReady = false;
  const plan = await bpCreatePlan();
  if (!plan) return;
  bpCurrentPlanId = plan.id;
  bpCurrentPlan = plan;
  const summary = {
    id: plan.id,
    serviceDate: plan.serviceDate,
    candidates: [],
    status: plan.status,
  };
  bpPlanSummaries.unshift(summary);
  bpRenderPlanList(bpPlanSummaries);
  bpRenderEditor(plan);
}

async function bpRemoveCandidate(candidateId) {
  if (!bpCurrentPlan) return;
  bpEditorReady = false;
  bpCurrentPlan.candidates = (bpCurrentPlan.candidates || []).filter((c) => c.id !== candidateId);
  bpCurrentPlan.ordinances = (bpCurrentPlan.ordinances || []).filter((o) => o.candidateId !== candidateId);
  bpCurrentPlan.witnesses = (bpCurrentPlan.witnesses || []).filter((w) => w.candidateId !== candidateId);
  bpRenderCandidates(bpCurrentPlan.candidates);
  bpRenderOrdinances(bpCurrentPlan.candidates, bpCurrentPlan.ordinances);
  bpRenderWitnesses(bpCurrentPlan.candidates, bpCurrentPlan.witnesses);
  bpEditorReady = true;
  bpAutoSave();
}

function bpHandleAddCandidate() {
  if (!bpCurrentPlan) return;
  bpEditorReady = false;
  const newId = `c_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  const newCandidate = {
    id: newId,
    fullName: "",
    birthDate: "",
    age: "",
    candidateType: "Convert",
    interviewCompleted: false,
    interviewedBy: "",
  };
  bpCurrentPlan.candidates = [...(bpCurrentPlan.candidates || []), newCandidate];
  bpCurrentPlan.ordinances = [...(bpCurrentPlan.ordinances || []), { candidateId: newId, baptizerName: "", baptizerPriesthood: "", confirmationBy: "" }];
  bpCurrentPlan.witnesses = [...(bpCurrentPlan.witnesses || []), { candidateId: newId, witness1: "", witness2: "" }];
  bpRenderCandidates(bpCurrentPlan.candidates);
  bpRenderOrdinances(bpCurrentPlan.candidates, bpCurrentPlan.ordinances);
  bpRenderWitnesses(bpCurrentPlan.candidates, bpCurrentPlan.witnesses);
  bpEditorReady = true;
  bpAutoSave();
}

async function initBaptismalPlanView() {
  if (bpViewInitialized) return;
  bpViewInitialized = true;
  const plans = await bpFetchPlans();
  bpPlanSummaries = plans;
  bpRenderPlanList(plans);
}

// ── PDF Export ────────────────────────────────────────────────────────────

function bpExportPdf() {
  if (!bpCurrentPlan) return;
  const plan = bpCollectPlanData();
  const dateStr = plan.serviceDate
    ? plan.serviceDate
    : "sem-data";
  const statusPt = BP_STATUS_PT[plan.status] || plan.status;

  const candidateRows = (plan.candidates || []).map((c, i) => {
    const typePt = BP_CANDIDATE_TYPE_PT[c.candidateType] || c.candidateType;
    const interv = c.interviewCompleted ? "Sim" : "Não";
    return `<tr>
      <td>${i + 1}</td><td>${_esc(c.fullName)}</td><td>${_esc(c.birthDate)}</td>
      <td>${_esc(c.age)}</td><td>${typePt}</td>
      <td>${interv}</td><td>${_esc(c.interviewedBy)}</td>
    </tr>`;
  }).join("");

  const ordMap = {};
  (plan.ordinances || []).forEach((o) => { ordMap[o.candidateId] = o; });
  const witMap = {};
  (plan.witnesses || []).forEach((w) => { witMap[w.candidateId] = w; });

  const ordRows = (plan.candidates || []).map((c) => {
    const o = ordMap[c.id] || {};
    const priPt = BP_PRIESTHOOD_PT[o.baptizerPriesthood] || o.baptizerPriesthood || "";
    return `<tr>
      <td>${_esc(c.fullName)}</td>
      <td>${_esc(o.baptizerName || "")}</td>
      <td>${priPt}</td>
      <td>${_esc(o.confirmationBy || "")}</td>
    </tr>`;
  }).join("");

  const witRows = (plan.candidates || []).map((c) => {
    const w = witMap[c.id] || {};
    return `<tr>
      <td>${_esc(c.fullName)}</td>
      <td>${_esc(w.witness1 || "")}</td>
      <td>${_esc(w.witness2 || "")}</td>
    </tr>`;
  }).join("");

  const progRows = (plan.program || []).map((item) =>
    `<tr><td>${_esc(item.item)}</td><td>${_esc(item.assignee || "")}</td></tr>`
  ).join("");

  const html = `<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<title>baptismo-${dateStr}</title>
<style>
  body { font-family: Arial, sans-serif; font-size: 12px; color: #222; margin: 24px; }
  h1 { font-size: 18px; margin-bottom: 4px; }
  h2 { font-size: 14px; margin: 20px 0 8px; border-bottom: 1px solid #aaa; padding-bottom: 4px; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
  th, td { border: 1px solid #ccc; padding: 5px 8px; text-align: left; }
  th { background: #f0f0f0; font-weight: 600; }
  .meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 24px; margin-bottom: 12px; }
  .meta-item { font-size: 12px; }
  .meta-label { color: #666; font-size: 11px; }
  .notes { background: #f9f9f9; border: 1px solid #ddd; padding: 8px; border-radius: 4px; white-space: pre-wrap; }
  @media print { body { margin: 12px; } }
</style>
</head><body>
<h1>Planejamento Batismal</h1>
<div class="meta-grid">
  <div class="meta-item"><span class="meta-label">Data do Batismo</span><br>${_esc(bpFormatDate(plan.serviceDate))}</div>
  <div class="meta-item"><span class="meta-label">Horário</span><br>${_esc(plan.serviceTime || "")}</div>
  <div class="meta-item"><span class="meta-label">Ala</span><br>${_esc(plan.ward || "")}</div>
  <div class="meta-item"><span class="meta-label">Local</span><br>${_esc(plan.location || "")}</div>
  <div class="meta-item"><span class="meta-label">Líder que preside</span><br>${_esc(plan.conductingLeader || "")}</div>
  <div class="meta-item"><span class="meta-label">Status</span><br>${_esc(statusPt)}</div>
</div>

<h2>Candidatos</h2>
<table><thead><tr>
  <th>#</th><th>Nome Completo</th><th>Nasc.</th><th>Idade</th><th>Tipo</th>
  <th>Entrevista</th><th>Entrevistado por</th>
</tr></thead><tbody>${candidateRows}</tbody></table>

<h2>Ordenanças</h2>
<table><thead><tr>
  <th>Candidato</th><th>Batizado por</th><th>Sacerdócio</th><th>Confirmado por</th>
</tr></thead><tbody>${ordRows}</tbody></table>

<h2>Testemunhas</h2>
<table><thead><tr>
  <th>Candidato</th><th>Testemunha 1</th><th>Testemunha 2</th>
</tr></thead><tbody>${witRows}</tbody></table>

<h2>Programa da Reunião</h2>
<table><thead><tr><th>Momento</th><th>Responsável</th></tr></thead><tbody>${progRows}</tbody></table>

${plan.notes ? `<h2>Observações</h2><div class="notes">${_esc(plan.notes)}</div>` : ""}
<script>window.onload = function(){ window.print(); }<\/script>
</body></html>`;

  const win = window.open("", "_blank");
  if (!win) return;
  win.document.write(html);
  win.document.title = `baptismo-${dateStr}`;
  win.document.close();
}

// ── Wire up Baptismal Plan events ─────────────────────────────────────────

bpNewPlanBtn.addEventListener("click", bpHandleNewPlan);
bpAddCandidateBtn.addEventListener("click", bpHandleAddCandidate);
bpExportPdfBtn.addEventListener("click", bpExportPdf);

[bpServiceDate, bpServiceTime, bpWard, bpLocation, bpConductingLeader].forEach((el) => {
  el.addEventListener("blur", () => { if (bpEditorReady) bpAutoSave(); });
});
bpStatus.addEventListener("change", () => { if (bpEditorReady) bpAutoSave(); });
bpNotes.addEventListener("blur", () => { if (bpEditorReady) bpAutoSave(); });

onAuthStateChanged(auth, (user) => {
  if (!user) {
    calendarView.classList.add("hidden");
    baptismalPlanView.classList.add("hidden");
    menuToggleBtn.classList.add("hidden");
    loginView.classList.remove("hidden");
    loginStatusEl.textContent = "";
    loginSpinner.classList.add("hidden");
    googleIcon.style.display = "";
    loginBtnText.textContent = "Entrar com Google";
    googleLoginBtn.disabled = false;
    currentWard = "";
    currentRoute = "/calendar";
    bpCurrentPlanId = null;
    bpCurrentPlan = null;
    bpPlanSummaries = [];
    bpViewInitialized = false;
    closeDrawer();
    updateDrawerUser(null);
    return;
  }

  loginView.classList.add("hidden");
  menuToggleBtn.classList.remove("hidden");
  if (currentRoute === "/baptismal-plan") {
    baptismalPlanView.classList.remove("hidden");
  } else {
    calendarView.classList.remove("hidden");
  }
  updateDrawerUser(user);
  if (!isCalendarInitialized) {
    renderHeader();
    setDefaultMonth();
    isCalendarInitialized = true;
  }
  loadSettings();
  fetchCalendar();
});
