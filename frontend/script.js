const API_URL = "http://127.0.0.1:8000";

let accessToken = localStorage.getItem("accessToken");

// ---------------- SHOW LOGIN ----------------

function showLogin() {
    document.getElementById("login-section").classList.remove("hidden");
    document.getElementById("register-section").classList.add("hidden");
}


// ---------------- SHOW REGISTER ----------------

function showRegister() {
    document.getElementById("login-section").classList.add("hidden");
    document.getElementById("register-section").classList.remove("hidden");
}


// ---------------- REGISTER ----------------

async function register() {

    const name = document.getElementById("register-name").value;
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;
    const skills = document.getElementById("register-skills").value;

    const message = document.getElementById("register-message");

    try {

        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                name: name,
                email: email,
                password: password,
                skills: skills,
                resume: null
            })
        });

        const data = await response.json();

        if (response.ok) {

            message.innerText = "Registration successful!";

            setTimeout(() => {
                showLogin();
            }, 1000);

        } else {

            message.innerText = data.detail || "Registration failed";

        }

    } catch (error) {

        message.innerText = "Server connection failed.";

        console.error(error);

    }
}


// ---------------- LOGIN ----------------

async function login() {

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    const message = document.getElementById("login-message");

    try {

        const response = await fetch(
            `${API_URL}/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
            {
                method: "POST"
            }
        );

        const data = await response.json();

        if (response.ok) {

            accessToken = data.access_token;

            localStorage.setItem(
                "accessToken",
                accessToken
            );

            message.innerText = "Login successful!";

            showDashboard();

        } else {

            message.innerText =
                data.detail || "Invalid email or password";

        }

    } catch (error) {

        message.innerText = "Server connection failed.";

        console.error(error);

    }
}


// ---------------- DASHBOARD ----------------

function showDashboard() {

    document
        .getElementById("login-section")
        .classList.add("hidden");

    document
        .getElementById("register-section")
        .classList.add("hidden");

    document
        .getElementById("dashboard-section")
        .classList.remove("hidden");

    loadProfile();

}


// ---------------- PROFILE ----------------

async function loadProfile() {

    try {

        const response = await fetch(
            `${API_URL}/profile`,
            {
                headers: {
                    "Authorization": `Bearer ${accessToken}`
                }
            }
        );

        const data = await response.json();

        if (response.ok) {

            document.getElementById("student-info").innerHTML = `
                <p><strong>Name:</strong> ${data.name}</p>
                <p><strong>Email:</strong> ${data.email}</p>
                <p><strong>Skills:</strong> ${data.skills || "Not added"}</p>
            `;

        } else {

            console.log(data);

        }

    } catch (error) {

        console.error(error);

    }
}


// ---------------- LOAD JOBS ----------------

async function loadJobs() {

    const jobsSection =
        document.getElementById("jobs-section");

    const jobsList =
        document.getElementById("jobs-list");

    jobsSection.classList.remove("hidden");

    jobsList.innerHTML = "Loading jobs...";

    try {

        const response = await fetch(
            `${API_URL}/jobs`
        );

        const data = await response.json();

        if (!response.ok) {

            jobsList.innerText = "Unable to load jobs.";
            return;

        }

        if (data.jobs.length === 0) {

            jobsList.innerText = "No jobs available.";
            return;

        }

        jobsList.innerHTML = "";

        data.jobs.forEach(job => {

            const jobCard = document.createElement("div");

            jobCard.className = "job-card";

            jobCard.innerHTML = `
                <h3>${job.job_title}</h3>

                <p>
                    <strong>Company:</strong>
                    ${job.company}
                </p>

                <p>
                    <strong>Location:</strong>
                    ${job.location}
                </p>

                <p>
                    <strong>Salary:</strong>
                    ${job.salary}
                </p>

                <p>
                    <strong>Skills:</strong>
                    ${job.skills_required}
                </p>

                <p>
                    <strong>Job Type:</strong>
                    ${job.job_type}
                </p>

                <button onclick="applyJob(${job.job_id})">
                    Apply
                </button>
            `;

            jobsList.appendChild(jobCard);

        });

    } catch (error) {

        jobsList.innerText =
            "Server connection failed.";

        console.error(error);

    }
}


// ---------------- APPLY JOB ----------------

async function applyJob(jobId) {

    try {

        const response = await fetch(
            `${API_URL}/jobs/${jobId}/apply`,
            {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${accessToken}`
                }
            }
        );

        const data = await response.json();

        if (response.ok) {

            alert(
                "Job application submitted successfully!"
            );

            loadApplications();

        } else {

            alert(
                data.detail || "Application failed"
            );

        }

    } catch (error) {

        alert("Server connection failed.");

        console.error(error);

    }
}


// ---------------- MY APPLICATIONS ----------------

async function loadApplications() {

    const applicationsSection =
        document.getElementById(
            "applications-section"
        );

    const applicationsList =
        document.getElementById(
            "applications-list"
        );

    applicationsSection.classList.remove("hidden");

    applicationsList.innerHTML =
        "Loading applications...";

    try {

        const response = await fetch(
            `${API_URL}/my-applications`,
            {
                headers: {
                    "Authorization":
                        `Bearer ${accessToken}`
                }
            }
        );

        const data = await response.json();

        if (!response.ok) {

            applicationsList.innerText =
                data.detail || "Unable to load applications.";

            return;

        }

        if (data.applications.length === 0) {

            applicationsList.innerText =
                "You have not applied for any job yet.";

            return;

        }

        applicationsList.innerHTML = "";

        data.applications.forEach(application => {

            const card =
                document.createElement("div");

            card.className =
                "application-card";

            card.innerHTML = `
                <h3>${application.job_title}</h3>

                <p>
                    <strong>Company:</strong>
                    ${application.company}
                </p>

                <p>
                    <strong>Location:</strong>
                    ${application.location}
                </p>

                <p>
                    <strong>Salary:</strong>
                    ${application.salary}
                </p>

                <p class="status">
                    Status:
                    ${application.status}
                </p>
            `;

            applicationsList.appendChild(card);

        });

    } catch (error) {

        applicationsList.innerText =
            "Server connection failed.";

        console.error(error);

    }
}


// ---------------- LOGOUT ----------------

function logout() {

    localStorage.removeItem("accessToken");

    accessToken = null;

    document
        .getElementById("dashboard-section")
        .classList.add("hidden");

    showLogin();

    document.getElementById("login-message").innerText =
        "You have been logged out.";

}