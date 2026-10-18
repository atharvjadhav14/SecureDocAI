
"use strict";

const API_BASE = "";
let COMPANY_ID = null;
const TOKEN_KEY = "securedoc_access_token";
const EMAIL_KEY = "securedoc_user_email";

const $ = (selector) => document.querySelector(selector);

const loginScreen = $("#loginScreen");
const appScreen = $("#appScreen");
const loginForm = $("#loginForm");
const loginButton = $("#loginButton");
const loginMessage = $("#loginMessage");
const userEmail = $("#userEmail");

let busy = false;
let currentRole = null;
function setMessage(element, message, success = false) {
    element.textContent = message;
    element.classList.toggle("success", success);
}

function getToken() {
    return sessionStorage.getItem(TOKEN_KEY);
}

function setBusy(button, value, label) {
    button.disabled = value;
    button.style.opacity = value ? "0.7" : "1";
    button.textContent = value ? "Please wait..." : label;
}

async function apiRequest(path, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = getToken();

    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers
    });

    if (response.status === 401 && token) {
        logout();
        throw new Error("Your session expired. Please sign in again.");
    }

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.detail || `Request failed (${response.status}).`);
    }

    return data;
}


async function loadMyWorkspace() {
    const result = await apiRequest("/me/workspaces");
    const workspaces = result.workspaces || [];

    if (workspaces.length === 0) {
        currentRole = null;
        COMPANY_ID = null;
        throw new Error(
            "Your account is not assigned to any workspace."
        );
    }

    // Automatically select the first workspace this user can access.
    const workspace = workspaces[0];

    COMPANY_ID = Number(workspace.company_id);
    currentRole = workspace.role;

    const roleLabel = $("#userRole");
    if (roleLabel) {
        roleLabel.textContent =
            currentRole === "admin"
                ? "Workspace administrator"
                : "Workspace member";
    }

    const workspaceName = document.querySelector(
        ".workspace-copy strong"
    );

    if (workspaceName) {
        workspaceName.textContent = workspace.company_name;
    }

const uploadCard = $("#uploadCard");

if (uploadCard) {
    uploadCard.classList.toggle("hidden", currentRole !== "admin");
}

}


function showApp() {
    loginScreen.classList.add("hidden");
    appScreen.classList.remove("hidden");
    userEmail.textContent = sessionStorage.getItem(EMAIL_KEY) || "Signed in";
    showView("chat");
}

function showLogin(message = "") {
    appScreen.classList.add("hidden");
    loginScreen.classList.remove("hidden");
    setMessage(loginMessage, message);
}

function logout() {
    currentRole = null;

    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(EMAIL_KEY);
    showLogin("You have been signed out.");
    $("#password").value = "";
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (busy) return;
    busy = true;
    setBusy(loginButton, true);

    setMessage(loginMessage, "");

    try {
        const email = $("#email").value.trim();
        const password = $("#password").value;

        const result = await fetch(`${API_BASE}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await result.json().catch(() => ({}));

        if (!result.ok) {
            throw new Error(data.detail || "Unable to sign in.");
        }

        if (!data.access_token) {
            throw new Error("The server did not return an access token.");
        }

        sessionStorage.setItem(TOKEN_KEY, data.access_token);
        sessionStorage.setItem(EMAIL_KEY, email);

        $("#password").value = "";

showApp();

try {
    await loadMyWorkspace();
    await loadDocuments();
} catch (error) {
    logout();
    setMessage(loginMessage, error.message);
}

    } catch (error) {
        setMessage(loginMessage, error.message);
    } finally {
        busy = false;
        setBusy(loginButton, false, "Sign in →");
    }
});

$("#logoutButton").addEventListener("click", logout);


function showView(view) {
    const isChat = view === "chat";
    const isDocuments = view === "documents";
    const isDashboard = view === "dashboard";

    $("#chatView").classList.toggle("hidden", !isChat);
    $("#documentsView").classList.toggle("hidden", !isDocuments);
    $("#dashboardView").classList.toggle("hidden", !isDashboard);

    $("#pageTitle").textContent = isDashboard
        ? "Dashboard"
        : isChat
            ? "AI Assistant"
            : "Documents";

    document.querySelectorAll(".nav-item").forEach((button) => {
        button.classList.toggle(
            "active",
            button.dataset.view === view
        );
    });

    if (isDocuments) {
        loadDocuments();
    }

    if (isDashboard) {
        loadDashboard();
    }
}

document.querySelectorAll(".nav-item").forEach((button) => {
    button.addEventListener("click", () => {
        showView(button.dataset.view);
    });
});


function addMessage(role, text) {
    const message = document.createElement("div");
    message.className = `message ${role}`;

    if (role === "assistant") {
        const label = document.createElement("div");
        label.className = "message-label";
        label.textContent = "SECUREDOC AI";
        message.appendChild(label);
    }

    const content = document.createElement("div");
    content.textContent = text;
    message.appendChild(content);

    $("#chatMessages").appendChild(message);
    message.scrollIntoView({ behavior: "smooth", block: "nearest" });

    return message;
}

function addSources(message, sources) {
    if (!Array.isArray(sources) || sources.length === 0) return;

    const list = document.createElement("div");
    list.className = "source-list";

    const heading = document.createElement("div");
    heading.className = "message-label";
    heading.textContent = "SOURCES";
    list.appendChild(heading);

    sources.forEach((source) => {
        const card = document.createElement("div");
        card.className = "source-card";

        const filename = document.createElement("strong");
        filename.textContent = source.filename || "Document";
        card.appendChild(filename);

        const excerpt = document.createElement("p");
        excerpt.textContent = source.content || "";
        card.appendChild(excerpt);

        if (Number.isFinite(Number(source.score))) {
            const score = document.createElement("span");
            score.className = "source-score";
            score.textContent =
                `Similarity score: ${Number(source.score).toFixed(4)}`;
            card.appendChild(score);
        }

        list.appendChild(card);
    });

    message.appendChild(list);
}

async function askQuestion(question) {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || busy) return;

    busy = true;
    $("#questionInput").value = "";
    $("#sendButton").disabled = true;

    addMessage("user", cleanQuestion);
    const waiting = addMessage("assistant", "Searching authorized documents...");

    try {
        const result = await apiRequest("/search", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                question: cleanQuestion,
                company_id: COMPANY_ID
            })
        });

        waiting.replaceChildren();

        const label = document.createElement("div");
        label.className = "message-label";
        label.textContent = "SECUREDOC AI";
        waiting.appendChild(label);

        const answer = document.createElement("div");
        answer.textContent = result.answer || "No answer was returned.";
        waiting.appendChild(answer);

        addSources(waiting, result.sources);
    } catch (error) {
        waiting.textContent = error.message;
    } finally {
        busy = false;
        $("#sendButton").disabled = false;
        $("#questionInput").focus();
    }
}

$("#chatForm").addEventListener("submit", (event) => {
    event.preventDefault();
    askQuestion($("#questionInput").value);
});

document.querySelectorAll(".suggestion").forEach((button) => {
    button.addEventListener("click", () => {
        showView("chat");
        askQuestion(button.dataset.question);
    });
});

async function loadDocuments() {
    const rows = $("#documentRows");
    rows.replaceChildren();

    const loadingRow = document.createElement("tr");
    const loadingCell = document.createElement("td");
    loadingCell.colSpan = 4;
    loadingCell.className = "table-empty";
    loadingCell.textContent = "Loading documents...";
    loadingRow.appendChild(loadingCell);
    rows.appendChild(loadingRow);

    setMessage($("#documentsMessage"), "");

    try {
        const result = await apiRequest(
            `/documents?company_id=${COMPANY_ID}`
        );

        rows.replaceChildren();

        const documents = result.documents || [];
        $("#documentCount").textContent =
            `${documents.length} ${documents.length === 1 ? "file" : "files"}`;

        if (documents.length === 0) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");
            td.colSpan = 4;
            td.className = "table-empty";
            td.textContent = "No documents uploaded yet.";
            tr.appendChild(td);
            rows.appendChild(tr);
            return;
        }


documents.forEach((doc) => {
    const tr = document.createElement("tr");

    const nameCell = document.createElement("td");
    const name = document.createElement("div");
    name.className = "file-name";

    const icon = document.createElement("span");
    icon.className = "file-icon";
    icon.textContent = doc.filename.toLowerCase().endsWith(".pdf")
        ? "PDF"
        : "TXT";

    const filename = document.createElement("span");
    filename.textContent = doc.filename;

    name.append(icon, filename);
    nameCell.appendChild(name);

    const idCell = document.createElement("td");
    idCell.textContent = String(doc.id);

    const dateCell = document.createElement("td");
    dateCell.textContent = doc.created_at || "—";


const actionCell = document.createElement("td");

if (currentRole === "admin") {
    const deleteButton = document.createElement("button");
    deleteButton.className = "delete-button";
    deleteButton.textContent = "Delete";

    deleteButton.addEventListener("click", () => {
        deleteDocument(doc.id, doc.filename);
    });

    actionCell.appendChild(deleteButton);
} else {
    actionCell.textContent = "View only";
}

    tr.append(nameCell, idCell, dateCell, actionCell);
    rows.appendChild(tr);
});

    } catch (error) {
        rows.replaceChildren();
        setMessage($("#documentsMessage"), error.message);
    }
}


async function loadDashboard() {
    const message = $("#dashboardMessage");
    setMessage(message, "Loading workspace statistics...");

    try {
        if (currentRole !== "admin") {
            throw new Error(
                "The dashboard is available to workspace administrators only."
            );
        }

        if (COMPANY_ID === null) {
            throw new Error("No active workspace is selected.");
        }

        const result = await apiRequest(
            `/dashboard/summary?company_id=${COMPANY_ID}`
        );

        $("#statDocuments").textContent = result.total_documents ?? 0;
        $("#statChunks").textContent = result.total_chunks ?? 0;
        $("#statRole").textContent =
            result.workspace?.role || currentRole;
        $("#statWorkspace").textContent =
            result.workspace?.company_name || "Active workspace";

        const rows = $("#recentDocumentRows");
        rows.replaceChildren();

        const documents = result.recent_documents || [];

        if (documents.length === 0) {
            const tr = document.createElement("tr");
            const td = document.createElement("td");

            td.colSpan = 3;
            td.className = "table-empty";
            td.textContent = "No documents have been added yet.";

            tr.appendChild(td);
            rows.appendChild(tr);
        } else {
            documents.forEach((doc) => {
                const tr = document.createElement("tr");

                const nameCell = document.createElement("td");
                const name = document.createElement("div");
                name.className = "file-name";

                const icon = document.createElement("span");
                icon.className = "file-icon";
                icon.textContent = doc.filename.toLowerCase().endsWith(".pdf")
                    ? "PDF"
                    : "TXT";

                const filename = document.createElement("span");
                filename.textContent = doc.filename;

                name.append(icon, filename);
                nameCell.appendChild(name);

                const idCell = document.createElement("td");
                idCell.textContent = String(doc.id);

                const dateCell = document.createElement("td");
                dateCell.textContent = doc.created_at || "—";

                tr.append(nameCell, idCell, dateCell);
                rows.appendChild(tr);
            });
        }

        setMessage(message, "");
    } catch (error) {
        setMessage(message, error.message);
    }
}

$("#refreshDocuments").addEventListener("click", loadDocuments);
$("#refreshDashboard").addEventListener("click", loadDashboard);

$("#dashboardViewDocuments").addEventListener("click", () => {
    showView("documents");
});
$("#uploadForm").addEventListener("submit", async (event) => {
    event.preventDefault();

    const fileInput = $("#documentFile");
    const file = fileInput.files[0];

    if (!file) {
        setMessage($("#uploadMessage"), "Choose a PDF or TXT file.");
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        setMessage($("#uploadMessage"), "The file must be 10 MB or smaller.");
        return;
    }

    const extension = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "txt"].includes(extension)) {
        setMessage($("#uploadMessage"), "Only PDF and TXT files are supported.");
        return;
    }

    const button = $("#uploadButton");
    button.disabled = true;
    button.textContent = "Uploading...";
    setMessage($("#uploadMessage"), "");

    try {
        const formData = new FormData();
        formData.append("company_id", String(COMPANY_ID));
        formData.append("file", file);

        const result = await apiRequest("/documents/upload", {
            method: "POST",
            body: formData
        });

        fileInput.value = "";
        setMessage(
            $("#uploadMessage"),
            result.message || "Document uploaded successfully.",
            true
        );
        await loadDocuments();
    } catch (error) {
        setMessage($("#uploadMessage"), error.message);
    } finally {
        button.disabled = false;
        button.textContent = "Upload file";
    }
});

async function deleteDocument(id, filename) {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) {
        return;
    }

    try {
        const result = await apiRequest(
            `/documents/${id}?company_id=${COMPANY_ID}`,
            { method: "DELETE" }
        );

        setMessage(
            $("#documentsMessage"),
            result.message || "Document deleted.",
            true
        );
        await loadDocuments();
    } catch (error) {
        setMessage($("#documentsMessage"), error.message);
    }
}

// Restore the current tab's session after a page refresh.
if (getToken()) {
    showApp();

    loadMyWorkspace()
        .then(() => loadDocuments())
        .catch((error) => {
            logout();
            setMessage(loginMessage, error.message);
        });
} else {
    showLogin();
}
