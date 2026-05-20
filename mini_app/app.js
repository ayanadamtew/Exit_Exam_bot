// Global App State Management
let tg = null;
let currentQuestions = [];
let quizIndex = 0;
let quizScore = 0;
let userAnswers = [];

// Fallback practice questions database
const DEFAULT_PRACTICE_QUESTIONS = [
    {
        question: "What does the SQL command 'SELECT' do?",
        option_a: "Deletes data from the database",
        option_b: "Inserts new rows into a database table",
        option_c: "Retrieves rows of data from one or more tables",
        option_d: "Modifies existing database records",
        answer: "C"
    },
    {
        question: "Which of the following is NOT a fundamental search algorithm?",
        option_a: "Depth-First Search (DFS)",
        option_b: "Breadth-First Search (BFS)",
        option_c: "Uniform Cost Search (UCS)",
        option_d: "Recursive Bubble Search (RBS)",
        answer: "D"
    },
    {
        question: "What is the primary key of a database table used for?",
        option_a: "Uniquely identifying each record in the table",
        option_b: "Encrypting highly confidential database fields",
        option_c: "Linking multiple databases together over the web",
        option_d: "Executing background asynchronous script jobs",
        answer: "A"
    },
    {
        question: "In Python, which keyword is used to define an asynchronous function?",
        option_a: "await",
        option_b: "async",
        option_c: "defer",
        option_d: "thread",
        answer: "B"
    },
    {
        question: "Which data structure is typically used to implement Breadth-First Search (BFS)?",
        option_a: "Stack",
        option_b: "Queue",
        option_c: "Binary Tree",
        option_d: "Hash Map",
        answer: "B"
    }
];

// Initialize application on DOM ready
document.addEventListener("DOMContentLoaded", () => {
    initTelegram();
    initScreenNavigation();
    initCsvUploader();
});

// Setup Telegram WebApp Configuration
function initTelegram() {
    if (window.Telegram && window.Telegram.WebApp) {
        tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        
        // Fetch Telegram User Information
        const user = tg.initDataUnsafe?.user;
        if (user) {
            document.getElementById("user-name").innerText = `${user.first_name} ${user.last_name || ""}`.trim();
            if (user.photo_url) {
                document.getElementById("user-avatar").src = user.photo_url;
            } else {
                document.getElementById("user-avatar").src = `https://api.dicebear.com/7.x/initials/svg?seed=${user.first_name}`;
            }
        }
    }
}

// Screen Transition Management
function initScreenNavigation() {
    const btnQuickPlay = document.getElementById("btn-quick-play");
    const btnQuitQuiz = document.getElementById("btn-quit-quiz");
    const btnNextQuestion = document.getElementById("btn-next-question");
    const btnReturnHome = document.getElementById("btn-return-home");

    // Practice Mode Launcher
    btnQuickPlay.addEventListener("click", () => {
        startQuizSession(DEFAULT_PRACTICE_QUESTIONS);
    });

    // Quit active quiz session
    btnQuitQuiz.addEventListener("click", () => {
        if (confirm("Are you sure you want to abort the current quiz session?")) {
            showScreen("screen-dashboard");
        }
    });

    // Next button click
    btnNextQuestion.addEventListener("click", () => {
        advanceQuiz();
    });

    // Scoreboard return to home
    btnReturnHome.addEventListener("click", () => {
        showScreen("screen-dashboard");
    });
}

// CSV File Upload Controls
function initCsvUploader() {
    const uploadZone = document.getElementById("upload-zone");
    const csvInput = document.getElementById("csv-input");

    uploadZone.addEventListener("click", () => csvInput.click());

    // Drag-over styling states
    uploadZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadZone.classList.add("dragover");
    });

    uploadZone.addEventListener("dragleave", () => {
        uploadZone.classList.remove("dragover");
    });

    uploadZone.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadZone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleUploadedFile(e.dataTransfer.files[0]);
        }
    });

    csvInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleUploadedFile(e.target.files[0]);
        }
    });
}

// Read and Parse CSV Questions Data
function handleUploadedFile(file) {
    if (!file.name.endsWith(".csv")) {
        alert("Please upload a valid .csv questions database file!");
        return;
    }

    const reader = new FileReader();
    reader.onload = function(e) {
        const text = e.target.result;
        const questions = parseCsvData(text);
        
        if (questions && questions.length > 0) {
            // Start Quiz
            startQuizSession(questions);

            // Send back to Telegram Bot if within SDK
            if (tg) {
                tg.sendData(JSON.stringify(questions));
            }
        } else {
            alert("No valid questions parsed. Verify headers: question, option_a, option_b, option_c, option_d, answer");
        }
    };
    reader.readAsText(file);
}

// Simple Robust Client-Side CSV Parser
function parseCsvData(csvText) {
    const lines = csvText.split(/\r?\n/);
    if (lines.length < 2) return null;

    // Parse Headers
    const headers = lines[0].split(",").map(h => h.trim().replace(/^["']|["']$/g, '').toLowerCase());
    const reqHeaders = ["question", "option_a", "option_b", "option_c", "option_d", "answer"];
    
    // Check missing headers
    const hasAllHeaders = reqHeaders.every(req => headers.includes(req));
    if (!hasAllHeaders) return null;

    const questions = [];
    const idxQuestion = headers.indexOf("question");
    const idxA = headers.indexOf("option_a");
    const idxB = headers.indexOf("option_b");
    const idxC = headers.indexOf("option_c");
    const idxD = headers.indexOf("option_d");
    const idxAns = headers.indexOf("answer");

    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        // Clean values, supports simple quoted columns
        const values = parseCsvLine(line);
        if (values.length < headers.length) continue;

        const q = values[idxQuestion];
        const optA = values[idxA];
        const optB = values[idxB];
        const optC = values[idxC];
        const optD = values[idxD];
        const ans = values[idxAns] ? values[idxAns].trim().toUpperCase() : "";

        if (q && optA && optB && optC && optD && ["A", "B", "C", "D"].includes(ans)) {
            questions.push({
                question: q,
                option_a: optA,
                option_b: optB,
                option_c: optC,
                option_d: optD,
                answer: ans
            });
        }
    }
    return questions;
}

// Custom parser to handle comma inside quotes
function parseCsvLine(line) {
    const result = [];
    let insideQuote = false;
    let entry = "";
    
    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"' || char === "'") {
            insideQuote = !insideQuote;
        } else if (char === ',' && !insideQuote) {
            result.push(entry.trim().replace(/^["']|["']$/g, ''));
            entry = "";
        } else {
            entry += char;
        }
    }
    result.push(entry.trim().replace(/^["']|["']$/g, ''));
    return result;
}

// Switch between panels
function showScreen(screenId) {
    document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
    document.getElementById(screenId).classList.add("active");
}

// Start Quiz Session Action
function startQuizSession(questions) {
    currentQuestions = questions;
    quizIndex = 0;
    quizScore = 0;
    userAnswers = [];
    
    showScreen("screen-quiz");
    renderCurrentQuestion();
}

// Populate UI for Current Question Card
function renderCurrentQuestion() {
    const q = currentQuestions[quizIndex];
    const total = currentQuestions.length;

    // Update Counter & Progress Indicator
    document.getElementById("quiz-question-counter").innerText = `Question ${quizIndex + 1} of ${total}`;
    const pct = ((quizIndex + 1) / total) * 100;
    document.getElementById("quiz-progress-indicator").style.width = `${pct}%`;

    // Question Text
    document.getElementById("display-question").innerText = q.question;

    // Reset and Render Option Panels
    const optionsContainer = document.getElementById("display-options");
    optionsContainer.innerHTML = "";

    const opts = [
        { letter: "A", text: q.option_a },
        { letter: "B", text: q.option_b },
        { letter: "C", text: q.option_c },
        { letter: "D", text: q.option_d }
    ];

    opts.forEach(opt => {
        const btn = document.createElement("button");
        btn.className = "option-card";
        btn.innerHTML = `
            <span class="option-letter">${opt.letter}</span>
            <span class="option-text">${escapeHtml(opt.text)}</span>
        `;
        btn.addEventListener("click", () => handleSelectOption(btn, opt.letter));
        optionsContainer.appendChild(btn);
    });

    // Disable Next Question button
    document.getElementById("btn-next-question").disabled = true;
}

// Answer Selection Action
function handleSelectOption(selectedBtn, selectedLetter) {
    const q = currentQuestions[quizIndex];
    const correctLetter = q.answer;
    
    // Disable all options
    const optionsContainer = document.getElementById("display-options");
    const optionCards = optionsContainer.querySelectorAll(".option-card");
    optionCards.forEach(card => card.classList.add("disabled"));

    const isCorrect = (selectedLetter === correctLetter);
    if (isCorrect) {
        selectedBtn.classList.add("correct");
        quizScore++;
    } else {
        selectedBtn.classList.add("incorrect");
        // Highlight correct option
        optionCards.forEach(card => {
            const letterSpan = card.querySelector(".option-letter");
            if (letterSpan && letterSpan.innerText === correctLetter) {
                card.classList.add("correct");
            }
        });
    }

    userAnswers.push({
        questionIndex: quizIndex,
        selected: selectedLetter,
        correct: correctLetter,
        isCorrect: isCorrect
    });

    // Enable next question button
    document.getElementById("btn-next-question").disabled = false;
    
    // Vibrate device if supported
    if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred(isCorrect ? "success" : "error");
    }
}

// Advance Quiz Index or Render Scores
function advanceQuiz() {
    quizIndex++;
    if (quizIndex < currentQuestions.length) {
        renderCurrentQuestion();
    } else {
        showResultsBoard();
    }
}

// Show Final Performance Board
function showResultsBoard() {
    const total = currentQuestions.length;
    const pct = Math.round((quizScore / total) * 100);

    document.getElementById("result-score-fraction").innerText = `${quizScore} / ${total}`;
    document.getElementById("result-score-percent").innerText = `${pct}% Accuracy`;

    document.getElementById("perf-correct").innerText = quizScore;
    document.getElementById("perf-incorrect").innerText = total - quizScore;

    let rating = "📚 Keep Studying!";
    if (pct === 100) {
        rating = "🏆 Academic Master!";
    } else if (pct >= 80) {
        rating = "🌟 High Achiever!";
    } else if (pct >= 50) {
        rating = "👍 Steady Progress!";
    }
    document.getElementById("perf-rating").innerText = rating;

    showScreen("screen-results");

    // Success Haptic Feedback celebration
    if (tg && tg.HapticFeedback) {
        tg.HapticFeedback.notificationOccurred("success");
    }
}

// Helper to escape HTML tags
function escapeHtml(str) {
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
