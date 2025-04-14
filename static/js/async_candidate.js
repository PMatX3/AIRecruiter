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
    if (!job.selected_candidates || job.selected_candidates.length === 0) {
      return;
    }

    // Sort candidates by score (using stable sort)
    job.selected_candidates.sort((a, b) => {
      return (
        b.score - a.score || a.candidate_name.localeCompare(b.candidate_name)
      );
    });

    const jobItem = document.createElement("div");
    jobItem.classList.add("job-item");

    // Job Header with Candidate Count
    jobItem.innerHTML = `
        <button class="job-header" data-target="job-${job.job_id}-candidates">
            <div class="job-title-container">
               
                <span><h2>${escapeHTML(job.job_title)}</h2></span>
                
            </div>
            
            <div class="accordion-icon"></div>
        </button>
        <div id="job-${job.job_id}-candidates" class="job-content"></div>
    `;

    const jobContent = jobItem.querySelector(".job-content");

    // Candidate Cards
    job.selected_candidates.forEach((candidate) => {
      const candidateCard = createCandidateCard(candidate, job); // Pass job to createCandidateCard
      jobContent.appendChild(candidateCard);
    });

    fragment.appendChild(jobItem);
  });

  // Accordion functionality for job headers
  var headers = document.querySelectorAll(".job-header");
  headers.forEach((header) => {
    header.addEventListener("click", () => {
      const target = header.getAttribute("data-target");
      const content = document.getElementById(target);
      if (content) {
        content.classList.toggle("active");
      }
    });
  });

  return fragment;
}
function getScoreBadgeClass(score) {
  if (score >= 80) return "score-high";
  if (score >= 60) return "score-medium";
  return "score-low";
}

function formatDate(dateString) {
  if (!dateString) return "Not Scheduled";
  var date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function createCandidateCard(candidate, job) {
  var card = document.createElement("div");
  card.className = "candidate-accordion";

  const candidateString = JSON.stringify(candidate).replace(/'/g, "&#39;");

  // Check if interview is past
  var isPastInterview =
    candidate.interview_date && new Date(candidate.interview_date) < new Date();

  // Determine scheduling button
  var schedulingButton = "";
  if (!candidate.interview_date) {
    schedulingButton = `

          <button class="btn btn-schedule" data-candidate-id="${candidate.candidate_id}"  onclick="showDatePopup(event, '${candidate.candidate_id}', '${candidate.candidate_name}', '${candidate.candidate_email}', '${job.job_id}')">
        <svg xmlns="http://www.w3.org/2000/svg" class="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                d="M8 7V3m8 4V3m-9 8h10M5 11h14a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2z" />
        </svg>
              Schedule Interview
          </button>
      `;
  } else if (isPastInterview) {
    schedulingButton = `
          <button class="btn btn-schedule">
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 11h14a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2z" />
              </svg>
              Reschedule
          </button>
      `;
  }

  card.innerHTML = `
      <div class="accordion-header" data-id="${
        candidate?.candidate_id || "Not Available"
      }">
    <div class="candidate-info">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span class="candidate-name">${
          candidate?.candidate_name || "Not Available"
        }</span>
        <span class="score-badge ${getScoreBadgeClass(candidate?.score || 0)}">
            ${candidate?.score ?? "Not Available"}
        </span>
    </div>
</div>
    <div class="status-indicator ${
      candidate?.selection_status === "Selected"
        ? "status-selected"
        : "status-rejected"
    }">
        ${candidate?.selection_status || "Pending"}
    </div>
</div>
<div class="accordion-content">
    <div class="feedback-grid">
        <div class="feedback-section">
            <div class="feedback-label">Interview Date</div>
            <div class="feedback-value int-date">${
              formatDate(candidate?.interview_date) || "Not Available"
            }</div>
        </div>
        <div class="feedback-section">
            <div class="feedback-label">Interview Round</div>
            <div class="feedback-value int-round ${
              candidate?.next_round === "Yes"
                ? "status-selected"
                : "status-rejected"
            }">
                ${candidate?.next_round || "Pending Interview Round"}
            </div>
        </div>
    </div>
    <div class="feedback-grid">
      <div class="feedback-section">
          <div class="feedback-label">Interviewer Message</div>
          <div class="feedback-value int-feedback">${
            candidate?.interviwer_feedback || "Not Available"
          }</div>
      </div>
      <div class="feedback-section">
          <div class="feedback-label">Selection Status</div>
          <div class="feedback-value int-status"> ${
            candidate?.selection_status || "Pending"
          }</div>
      </div>

    </div>
    <div class="action-buttons">
        <button class="btn btn-edit" 
                        onclick="editCandidate(event, this, '${
                          candidate.candidate_id || ""
                        }', '${job?.job_id || ""}')"
                        data-candidate='${JSON.stringify(candidate).replace(
                          /'/g,
                          "&#39;"
                        )}' >
              <svg xmlns="http://www.w3.org/2000/svg" class="icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Edit Feedback
          </button>
        ${schedulingButton}
    </div>
</div>

  `;
  return card;
}

function editCandidate(event, button, candidateId, jobId) {
  if (event) {
    event.preventDefault(); // Prevent default action
  }

  const candidateString = button.dataset.candidate;
  const candidate = JSON.parse(candidateString);

  // Find the accordion header based on candidateId
  var headerDiv = document.querySelector(`[data-id="${candidateId}"]`);

  if (!headerDiv) {
    console.error(`Error: Candidate ID ${candidateId} not found.`);
    return; // Exit function if the element does not exist
  }

  // Get the next sibling (accordion content)
  var contentDiv = headerDiv.nextElementSibling;

  if (!contentDiv || !contentDiv.classList.contains("accordion-content")) {
    console.error(
      `Error: Accordion content not found for candidate ID ${candidateId}.`
    );
    return; // Exit function if contentDiv does not exist or has the wrong class
  }

  // Store the existing content before modifying it (for cancel action)
  contentDiv.setAttribute("data-original-content", contentDiv.innerHTML);

  // Remove the "active" class and add the "edit-mode" class
  contentDiv.classList.remove("active");
  contentDiv.classList.add("edit-mode");

  // Render the edit form inside the accordion-content
  contentDiv.innerHTML = renderEditForm(candidate, candidateId, jobId);
}

// Function to render the edit form
function renderEditForm(candidate, candidateId, jobId) {
  const candidateString = JSON.stringify(candidate).replace(/'/g, "&#39;");

  console.log("^^^^^^^^^^^^^^^^^^ candidate", candidateString);
  return `
      <div class="feedback-grid">
          <div class="feedback-section">
              <div class="feedback-label">Selection Status
</div>
              <select class="selection" id="edit-selection-status-${candidateId}">
                  
                  <option value="Selected" ${
                    candidate?.selection_status === "Selected" ? "selected" : ""
                  }>Selected</option>
                  <option value="Rejected" ${
                    candidate?.selection_status === "Rejected" ? "selected" : ""
                  }>Rejected</option>
                  <option value="On Hold" ${
                    candidate?.selection_status === "On Hold" ? "selected" : ""
                  }>On Hold</option>
                  <option value="Pending" ${
                    candidate?.selection_status === "Pending" ? "selected" : ""
                  }>Pending</option>
                  <option value="Shortlisted" ${
                    candidate?.selection_status === "Shortlisted"
                      ? "selected"
                      : ""
                  }>Shortlisted</option>
                  <option value="Under Review" ${
                    candidate?.selection_status === "Under Review"
                      ? "selected"
                      : ""
                  }>Under Review</option>
                  <option value="Hired" ${
                    candidate?.selection_status === "Hired" ? "selected" : ""
                  }>Hired</option>
                  <option value="Offer Declined" ${
                    candidate?.selection_status === "Offer Declined"
                      ? "selected"
                      : ""
                  }>Offer Declined</option>
              </select>
          </div>
          <div class="feedback-section">
              <div class="feedback-label">Interview Round</div>
              <select class="selection" id="edit-next-status-${candidateId}">
                  <option value="" ${
                    !candidate?.next_round ? "selected" : ""
                  }>No Round Assigned</option>
                  <option value="Round 1" ${
                    candidate?.next_round === "round_1" ? "selected" : ""
                  }>Round 1</option>
                  <option value="Round 2" ${
                    candidate?.next_round === "round_2" ? "selected" : ""
                  }>Round 2</option>
                  <option value="Round 3" ${
                    candidate?.next_round === "round_3" ? "selected" : ""
                  }>Round 3</option>
              </select>
          </div>
      </div>
      <div class="feedback-grid">
          <div class="feedback-section">
              <div class="feedback-label">Interviewer Message</div>
              <textarea class="message" id="edit-feedback-${candidateId}" rows="3">${
    candidate?.interviwer_feedback || ""
  }</textarea>
          </div>
      </div>
      <div class="action-buttons">
          <button class="btn btn-save" onclick="saveFeedback('${candidateId}')">Save Feedback</button>
          <button class="btn btn-cancel" onclick="cancelEdit('${candidateId}')">Cancel</button>
      </div>
  `;
}

function cancelEdit(candidateId) {
  // Find the accordion content using candidateId
  var contentDiv = document.querySelector(
    `[data-id="${candidateId}"]`
  ).nextElementSibling;

  if (!contentDiv || !contentDiv.classList.contains("accordion-content")) {
    console.error(
      `Error: Accordion content not found for candidate ID ${candidateId}.`
    );
    return; // Exit function if contentDiv is not found
  }

  // Restore the original content (before editing)
  var originalContent = contentDiv.getAttribute("data-original-content");
  if (originalContent) {
    contentDiv.innerHTML = originalContent;
  }

  // Remove the "edit-mode" class and add back the "active" class
  contentDiv.classList.remove("edit-mode");
  contentDiv.classList.add("active");
}

function saveFeedback(candidateId) {
  // Find elements
  var nextRoundElement = document.getElementById(
    `edit-next-status-${candidateId}`
  );
  var selectionStatusElement = document.getElementById(
    `edit-selection-status-${candidateId}`
  );
  var messageElement = document.getElementById(`edit-feedback-${candidateId}`);

  // Safety check for missing elements
  if (!nextRoundElement || !selectionStatusElement || !messageElement) {
    console.error(
      `Error: One or more form fields are missing for candidate ID ${candidateId}.`
    );
    return;
  }

  // Get values
  var nextRound = nextRoundElement.value;
  var selectionStatus = selectionStatusElement.value;
  var feedback = messageElement.value;

  // Simulate database update (Replace with actual API call)
  console.log("Saving feedback for candidate", candidateId, {
    nextRound,
    selectionStatus,
    feedback,
  });

  fetch(`/save_feedback/${candidateId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      nextRound: nextRound,
      selectionStatus: selectionStatus,
      feedback: feedback,
    }),
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("Feedback saved:", data);

      // Update UI

      var contentDiv = document.querySelector(
        `[data-id="${candidateId}"]`
      ).nextElementSibling;

      if (!contentDiv || !contentDiv.classList.contains("accordion-content")) {
        console.error(
          `Error: Accordion content not found for candidate ID ${candidateId}.`
        );
        return; // Exit function if contentDiv is not found
      }

      var originalContent = contentDiv.getAttribute("data-original-content");
      if (originalContent) {
        contentDiv.innerHTML = originalContent;
      }

      // Update content
      contentDiv.querySelector(".int-feedback").textContent = feedback; // Example update
      contentDiv.querySelector(".int-status").textContent = selectionStatus; // Example update
      contentDiv.querySelector(".int-round").textContent = nextRound; // Example update

      // Remove "edit-mode" class and add "active" class
      contentDiv.classList.remove("edit-mode");
      contentDiv.classList.add("active");
    })
    .catch((error) => {
      console.error("Error saving feedback:", error);
    });
}

// Initialize accordion functionality
function initAccordion() {
  // Clear any existing content
  container.innerHTML = "";

  // Create and append candidate cards
  candidateData.forEach(function (candidate) {
    var card = createCandidateCard(candidate);
    container.appendChild(card);
  });

  // Add click event to accordion headers
  var headers = document.querySelectorAll(".accordion-header");
  headers.forEach(function (header) {
    header.addEventListener("click", function () {
      var content = this.nextElementSibling;
      content.classList.toggle("active");
    });
  });
}

// Utility function to prevent XSS attacks
function escapeHTML(str) {
  if (typeof str !== "string") {
    return ""; // Return an empty string if str is not a valid string
  }
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

      if (selectedDate.getTime() < new Date().getTime()) {
        showErrorPopup(
          "You cannot schedule a meeting in the past. Please select a valid date and time."
        );

        if (scheduleButton) {
          scheduleButton.disabled = true;
          scheduleButton.style.cursor = "not-allowed";
          scheduleButton.style.opacity = "0.6";
        }
      } else {
        if (scheduleButton) {
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

        // Add the click event listener ONCE when the button is created
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
            console.log(
              " ==== <><><> Schedule meeting Api called <><><> ========="
            );
            const data = await response.json();

            if (data.success) {
              showPopup("Interview is scheduled successfully!", true);
              const utcDateTime = luxon.DateTime.fromISO(
                data.scheduled_datetime
              );
              const localDateTime = utcDateTime.toLocaleString(
                luxon.DateTime.DATETIME_MED
              );
              window.location.reload();
            } else {
              const errorMessage =
                data.message || "Error: Failed to schedule the interview.";
              showPopup(errorMessage, false);
            }
          } catch (error) {
            console.error("Error scheduling interview:", error);
          } finally {
            showLoadingOverlay(false);

            if (fp) {
              fp.close();
            }
          }
        });
      }
    },
    onOpen: function () {
      setMinTime();
      const buttonRect = event.target.getBoundingClientRect();
      const calendarPopup = document.querySelector(".flatpickr-calendar");

      const screenWidth = window.innerWidth;
      const screenHeight = window.innerHeight;
      const calendarWidth = calendarPopup.offsetWidth;
      const calendarHeight = calendarPopup.offsetHeight;

      let left = buttonRect.left;
      let top = buttonRect.bottom + window.scrollY; // Consider scrolling

      // Check available space and adjust position
      const spaceBelow = screenHeight - buttonRect.bottom;
      const spaceAbove = buttonRect.top;
      const spaceRight = screenWidth - buttonRect.right;
      const spaceLeft = buttonRect.left;

      // Prefer bottom placement, otherwise place based on available space
      if (spaceBelow >= calendarHeight) {
        top = buttonRect.bottom + window.scrollY; // Below the button
      } else if (spaceAbove >= calendarHeight) {
        top = buttonRect.top - calendarHeight + window.scrollY; // Above the button
      }

      // Adjust left position to prevent overflow
      if (spaceRight < calendarWidth && spaceLeft >= calendarWidth) {
        left = buttonRect.right - calendarWidth; // Move left if right space is small
      }

      // Apply final positioning
      calendarPopup.style.left = `${left}px`;
      calendarPopup.style.top = `${top}px`;
      calendarPopup.style.position = "absolute";
      calendarPopup.style.zIndex = "1000";
    },
  });

  function setMinTime() {
    const now = new Date();
    const currentDate = flatpickr.formatDate(now, "Y-m-d");
    const selectedDate = fp.selectedDates[0]
      ? flatpickr.formatDate(fp.selectedDates[0], "Y-m-d")
      : null;

    if (selectedDate === currentDate || !selectedDate) {
      const hours = now.getHours().toString().padStart(2, "0");
      const minutes = now.getMinutes().toString().padStart(2, "0");
      fp.set("minTime", `${hours}:${minutes}`);
    } else {
      fp.set("minTime", null);
    }
  }

  fp.config.onChange.push(function (selectedDates) {
    setMinTime();
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

document.addEventListener("click", function (event) {
  const header = event.target.closest(".accordion-header");
  if (!header) return; // Exit if click is not on an accordion-header

  const content = header.nextElementSibling; // Get the corresponding content section

  if (content && content.classList.contains("accordion-content")) {
    content.classList.toggle("active"); // Toggle active class
  }
});

// Start the application
initApp();
