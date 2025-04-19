// Use modern async/await pattern with Promise caching for data fetching
let cachedCandidateData = null;
// Fetch data once and cache it
async function fetchCandidateData() {
  if (cachedCandidateData) return cachedCandidateData;

  try {
    const response = await fetch("/selected_candidates");
    cachedCandidateData = await response.json();
    return cachedCandidateData;
  } catch (error) {
    console.error("Error fetching candidate data:", error);
    throw error;
  }
}

// Preload data before DOM is ready
const preloadedDataPromise = fetchCandidateData();

// Create elements using DocumentFragment for better performance
function createJobElements(data) {
  const fragment = document.createDocumentFragment();

  if (!data.jobs || data.jobs.length === 0) {
    const noDataMessage = document.createElement("p");
    noDataMessage.textContent = "No matching profiles available at this time.";
    fragment.appendChild(noDataMessage);
    return fragment;
  }

  data.jobs.forEach((job) => {
    if (!job.selected_candidates || job.selected_candidates.length === 0)
      return;

    // Sort candidates by score (using stable sort for consistent results)
    job.selected_candidates.sort(
      (a, b) =>
        b.score - a.score || a.candidate_name.localeCompare(b.candidate_name)
    );
    console.log(" job. selected candidates : ", job.selected_candidates);

    const jobItem = document.createElement("div");
    jobItem.classList.add("job-item");

    // Use template literals for cleaner HTML generation
    jobItem.innerHTML = `
      <button class="job-header" data-target="job-${job.job_id}-candidates">
        <div class="job-title-container">
          <h2>${escapeHTML(job.job_title)}</h2>
          <p class="candidate-count text-sm text-gray">${
            job.selected_candidates.length
          } candidates</p>
        </div>
        <div class="accordion-icon"></div>
      </button>
      <div id="job-${job.job_id}-candidates" class="job-content"></div>
    `;

    const jobContent = jobItem.querySelector(".job-content");

    // Use DocumentFragment for better performance when adding multiple candidates
    const candidatesFragment = document.createDocumentFragment();

    job.selected_candidates.forEach((candidate) => {
      const candidateRow = document.createElement("div");
      candidateRow.classList.add("candidate-card");

      // Generate candidate info
      const candidateInfo = document.createElement("div");
      candidateInfo.classList.add("candidate-info");
      candidateInfo.innerHTML = `<h3>${escapeHTML(
        candidate.candidate_name
      )}</h3>`;
      candidateRow.appendChild(candidateInfo);

      // Generate candidate actions
      const candidateActions = document.createElement("div");
      candidateActions.classList.add("candidate-actions");

      // Score badge with class determined by score
      const scoreBadgeClass =
        candidate.score >= 85
          ? "score-high"
          : candidate.score >= 70
          ? "score-medium"
          : "";

      candidateActions.innerHTML = `
        <div class="score-badge ${scoreBadgeClass}">
          Score: ${candidate.score}
        </div>
      `;

      // Handle interview date display or schedule button
      if (candidate.interview_date) {
        const interviewUTC = luxon.DateTime.fromISO(candidate.interview_date);
        const userLocalDate = interviewUTC.toLocaleString(
          luxon.DateTime.DATETIME_MED
        );

        if (interviewUTC < luxon.DateTime.now()) {
          // Interview date in the past - show reschedule button
          const rescheduleButton = document.createElement("button");
          rescheduleButton.textContent = "Reschedule";
          rescheduleButton.classList.add("reschedule-btn");
          rescheduleButton.addEventListener("click", (event) => {
            showDatePopup(
              event,
              candidate.candidate_id,
              candidate.candidate_name,
              candidate.email,
              job.job_id,
              candidate
            );
          });
          candidateActions.appendChild(rescheduleButton);
        } else {
          // Interview date in the future - show date
          const dateDisplay = document.createElement("span");
          dateDisplay.textContent = userLocalDate;
          candidateActions.appendChild(dateDisplay);
        }
      } else {
        // No interview date - show date picker button
        const datePickerBtn = document.createElement("button");
        datePickerBtn.classList.add("date-picker-btn");
        datePickerBtn.innerHTML = '<i class="far fa-calendar-alt fa-lg"></i>';
        datePickerBtn.addEventListener("click", (event) => {
          showDatePopup(
            event,
            candidate.candidate_id,
            candidate.candidate_name,
            candidate.email,
            job.job_id
          );
        });
        candidateActions.appendChild(datePickerBtn);
      }

      candidateRow.appendChild(candidateActions);
      candidatesFragment.appendChild(candidateRow);
    });

    jobContent.appendChild(candidatesFragment);
    fragment.appendChild(jobItem);
  });

  return fragment;
}

// Utility function to prevent XSS attacks
function escapeHTML(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Initialize UI with event delegation for better performance
function initializeUI() {
  const jobsContainer = document.querySelector(".jobs-container");

  // Event delegation for accordion functionality
  jobsContainer.addEventListener("click", (event) => {
    const header = event.target.closest(".job-header");
    if (!header) return;

    const targetId = header.getAttribute("data-target");
    const targetContent = document.getElementById(targetId);

    // Close all other sections
    document.querySelectorAll(".job-content.show").forEach((content) => {
      if (content.id !== targetId) {
        content.classList.remove("show");
      }
    });

    // Toggle current section
    targetContent.classList.toggle("show");
  });

  // Search functionality with debounce
  const searchInput = document.getElementById("search");
  let searchDebounceTimer;

  searchInput.addEventListener("input", function () {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
      const searchTerm = this.value.toLowerCase();
      performSearch(searchTerm);
    }, 300); // 300ms debounce
  });

  // Load more functionality
  const loadMoreBtn = document.getElementById("loadMore");
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener("click", function () {
      this.textContent = "Loading...";
      this.disabled = true;

      // Simulate loading delay with Promise
      new Promise((resolve) => setTimeout(resolve, 1000)).then(() => {
        this.textContent = "No more candidates to load";
        this.style.opacity = "0.5";
        this.style.cursor = "not-allowed";
      });
    });
  }
}

// Optimized search with intersection observer for better performance
function performSearch(searchTerm) {
  const jobItems = document.querySelectorAll(".job-item");

  // If search term is empty, show all items
  if (!searchTerm) {
    jobItems.forEach((item) => {
      item.style.display = "block";
      item.querySelector(".job-content").classList.remove("show");
    });
    return;
  }

  jobItems.forEach((item) => {
    const jobTitle = item.querySelector("h2").textContent.toLowerCase();
    const candidateNames = Array.from(
      item.querySelectorAll(".candidate-info h3")
    ).map((name) => name.textContent.toLowerCase());

    // Check for matches
    const titleMatch = jobTitle.includes(searchTerm);
    const candidateMatch = candidateNames.some((name) =>
      name.includes(searchTerm)
    );

    // Show/hide based on match
    if (titleMatch || candidateMatch) {
      item.style.display = "block";

      // If searching by candidate, expand the section
      if (candidateMatch) {
        item.querySelector(".job-content").classList.add("show");
      }
    } else {
      item.style.display = "none";
    }
  });
}

// Modern popup system using web components
class PopupNotification extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  connectedCallback() {
    const type = this.getAttribute("type") || "info";
    const message = this.getAttribute("message") || "";

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          position: fixed;
          top: 20px;
          right: 20px;
          z-index: 10000;
          animation: slideIn 0.3s forwards;
        }
        .popup {
          padding: 15px 20px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          background: white;
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          max-width: 350px;
        }
        .popup-success { border-left: 4px solid #4CAF50; }
        .popup-error { border-left: 4px solid #F44336; }
        .popup-info { border-left: 4px solid #2196F3; }
        .close-btn {
          margin-left: 10px;
          cursor: pointer;
          background: none;
          border: none;
          font-size: 16px;
        }
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      </style>
      <div class="popup popup-${type}">
        <span>${message}</span>
        <button class="close-btn">×</button>
      </div>
    `;

    this.shadowRoot
      .querySelector(".close-btn")
      .addEventListener("click", () => {
        this.remove();
      });

    // Auto-remove after 5 seconds
    setTimeout(() => {
      if (this.isConnected) {
        this.remove();
      }
    }, 5000);
  }
}

// Register custom element
customElements.define("popup-notification", PopupNotification);

// Modern popup functions
function showSuccessPopup(message) {
  const popup = document.createElement("popup-notification");
  popup.setAttribute("type", "success");
  popup.setAttribute("message", message);
  document.body.appendChild(popup);
}

function showErrorPopup(message) {
  const popup = document.createElement("popup-notification");
  popup.setAttribute("type", "error");
  popup.setAttribute("message", message);
  document.body.appendChild(popup);
}

// Improved date picker with Flatpickr
function showDatePopup(
  event,
  candidate_id,
  candidateName,
  candidateEmail,
  jobId
) {
  // Remove any existing calendar popup
  const existingCalendarPopup = document.querySelector(".flatpickr-calendar");
  if (existingCalendarPopup) {
    existingCalendarPopup.remove();
  }

  // Create a container for the calendar
  const calendarContainer = document.createElement("div");
  calendarContainer.id = "calendarContainer";
  calendarContainer.classList.add("calendar-container");
  calendarContainer.style.position = "absolute";
  calendarContainer.style.zIndex = "1000";
  calendarContainer.style.left = event.clientX + "px";
  calendarContainer.style.top = event.clientY + "px";

  // Create an input element for flatpickr
  const flatpickrInput = document.createElement("input");
  flatpickrInput.type = "text";
  flatpickrInput.style.display = "none"; // Hide the input
  calendarContainer.appendChild(flatpickrInput);

  // Append the calendar container to the body
  document.body.appendChild(calendarContainer);

  let fp;
  fp = flatpickr(flatpickrInput, {
    enableTime: true,
    minDate: "today",
    dateFormat: "Y-m-d H:i",
    disableMobile: "true",
    onOpen: function (selectedDates, dateStr, instance) {
      const calendarPopup = document.querySelector(".flatpickr-calendar");
      if (calendarPopup) {
        // Adjust the position of the calendar popup to ensure it stays within the viewport
        const rect = calendarPopup.getBoundingClientRect();
        const windowWidth = window.innerWidth;
        const windowHeight = window.innerHeight;

        if (rect.right > windowWidth) {
          calendarPopup.style.left = windowWidth - rect.width - 10 + "px"; // 10px margin
        }

        if (rect.bottom > windowHeight) {
          calendarPopup.style.top = windowHeight - rect.height - 10 + "px";
        }
      }
    },
    onClose: function () {
      // Clean up the calendar container when closed
      if (calendarContainer) {
        calendarContainer.remove();
      }
      if (fp) {
        fp.destroy(); // Destroy the flatpickr instance
        fp = null;
      }
    },
    onChange: function (selectedDates) {
      const selectedDate = selectedDates[0];
      const now = new Date();

      const calendarPopup = document.querySelector(".flatpickr-calendar");
      let scheduleButton = calendarPopup.querySelector(".schedule-meeting-btn");

      if (scheduleButton) {
        if (selectedDate.getTime() < new Date().getTime()) {
          showErrorPopup(
            "You cannot schedule a meeting in the past. Please select a valid date and time."
          );

          scheduleButton.disabled = true;
          scheduleButton.style.cursor = "not-allowed";
          scheduleButton.style.opacity = "0.6";
        } else {
          scheduleButton.disabled = false;
          scheduleButton.style.cursor = "pointer";
          scheduleButton.style.opacity = 1;
        }
      }

      if (!scheduleButton) {
        scheduleButton = document.createElement("button");
        scheduleButton.textContent = "Schedule Meeting";
        scheduleButton.classList.add("schedule-meeting-btn");
        calendarPopup.appendChild(scheduleButton);
      }

      // // Enable the button if the selected date and time are valid
      // scheduleButton.disabled = false;
      // scheduleButton.classList.remove("disabled");

      // Add a click event listener to the "Schedule Meeting" button
      scheduleButton.addEventListener("click", async () => {
        const selectedDate = fp.selectedDates[0];
        const isoDateTime = selectedDate.toISOString();
        const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;

        showLoadingOverlay(true);

        try {
          const response = await fetch("/schedule_meeting", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              action: "schedule",
              candidate_id: candidate_id,
              candidate_name: candidateName,
              candidate_email: "devradhekrishna1@gmail.com",
              recruiter_email: "yourbestrecruiterai@gmail.com",
              datetime: isoDateTime,
              timezone: userTimezone,
              job_id: jobId,
            }),
          });

          const data = await response.json();

          if (data.success) {
            showPopup("Interview is scheduled successfully!", true); // Success message
            const utcDateTime = luxon.DateTime.fromISO(data.scheduled_datetime);
            const localDateTime = utcDateTime.toLocaleString(
              luxon.DateTime.DATETIME_MED
            );
            window.location.reload();
          } else {
            showPopup("Error: Failed to schedule the interview.", false); // Error message
          }
        } catch (error) {
          console.error("Error scheduling interview:", error);
        } finally {
          // Hide the loader
          showLoadingOverlay(false);

          // Close the calendar popup
          if (fp) {
            fp.close();
          }
        }
      });
    },
  });

  const calendarPopup = document.querySelector(".flatpickr-calendar");
  calendarContainer.appendChild(calendarPopup);
  // Open the calendar popup
  fp.open();

  // Prevent the event from propagating to the document
  event.stopPropagation();
}

// Async function to schedule an interview
function setInterviewDateTime(text) {
  let candidateActions = document.querySelector(".candidate-actions");

  let newSpan = document.createElement("span");
  newSpan.textContent = text; // Set the text

  // Append the new span inside .candidate-actions
  candidateActions.appendChild(newSpan);
}

function showPopup(message, isSuccess = true) {
  // Check if the popup already exists
  let existingPopup = document.getElementById("confirmationPopup");
  if (existingPopup) {
    existingPopup.remove(); // Remove if it exists to prevent duplication
  }

  // Create the popup container
  let popup = document.createElement("div");
  popup.id = "confirmationPopup";
  popup.className = "confirm-popup";
  popup.style.display = "block";

  // Create popup content
  let popupContent = document.createElement("div");
  popupContent.className = "popup-content";

  // Create heading
  let heading = document.createElement("h3");
  heading.textContent = isSuccess ? "Success" : "Error"; // Change heading based on success/error

  // Create message paragraph
  let messagePara = document.createElement("p");
  messagePara.textContent = message;

  // Create actions div
  let popupActions = document.createElement("div");
  popupActions.className = "popup-actions";

  // Create OK button
  let okButton = document.createElement("button");
  okButton.textContent = "Okay";
  okButton.className = isSuccess ? "btn btn-success" : "btn btn-danger"; // Different color for success/error
  okButton.onclick = closePopup;

  // Append elements
  popupActions.appendChild(okButton);
  popupContent.appendChild(heading);
  popupContent.appendChild(messagePara);
  popupContent.appendChild(popupActions);
  popup.appendChild(popupContent);

  // Append popup to body
  document.body.appendChild(popup);
}

// Function to close the popup
function closePopup() {
  let popup = document.getElementById("confirmationPopup");
  if (popup) {
    popup.style.display = "none";
    popup.remove();
  }
}

let overlay = null; // Declare overlay in a scope accessible to the function

// Loading overlay
function showLoadingOverlay(show) {
  if (show) {
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = "loading-overlay";
      overlay.innerHTML = `
        <div class="loader-container">
          <div class="modern-loader"></div>
        </div>
      `;
      document.body.appendChild(overlay);
    }
    overlay.classList.add("active"); // Add the "active" class
  } else if (overlay) {
    overlay.classList.remove("active"); // Remove the "active" class
  }
}

// Convert UTC to local time
function convertUTCtoLocal(utcDateTime) {
  return luxon.DateTime.fromISO(utcDateTime).toLocaleString(
    luxon.DateTime.DATETIME_MED
  );
}

// Refresh data and update UI
async function refreshCandidateData() {
  // Clear cache to force refresh
  cachedCandidateData = null;

  try {
    const data = await fetchCandidateData();
    const jobsContainer = document.querySelector(".jobs-container");

    // Clear and repopulate
    jobsContainer.innerHTML = "";
    jobsContainer.appendChild(createJobElements(data));
  } catch (error) {
    console.error("Error refreshing data:", error);
    showErrorPopup("Failed to refresh candidate data.");
  }
}

// Main initialization function with lazy loading for non-critical resources
async function initApp() {
  try {
    // Fetch data before DOM is fully loaded (preloading)
    const data = await preloadedDataPromise;

    // Initialize UI when DOM is ready
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        const jobsContainer = document.querySelector(".jobs-container");
        jobsContainer.innerHTML = "";
        jobsContainer.appendChild(createJobElements(data));
        initializeUI();
      });
    } else {
      // DOM already loaded
      const jobsContainer = document.querySelector(".jobs-container");
      jobsContainer.innerHTML = "";
      jobsContainer.appendChild(createJobElements(data));
      initializeUI();
    }

    // Lazy load non-critical resources
    if ("IntersectionObserver" in window) {
      const lazyLoadElements = document.querySelectorAll(".lazy-load");
      const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const element = entry.target;
            // Load resources
            observer.unobserve(element);
          }
        });
      });

      lazyLoadElements.forEach((element) => observer.observe(element));
    }
  } catch (error) {
    console.error("Application initialization error:", error);
    showErrorPopup("Failed to initialize the application.");
  }
}

// Start the application
initApp();
