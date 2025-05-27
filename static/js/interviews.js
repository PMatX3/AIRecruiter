async function fetchAndProcessInterviews() {
  try {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const response = await fetch(
      `/get_All_interviews?timezone=${encodeURIComponent(timezone)}`
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const interviews = await response.json();
    return interviews; // Return the data
  } catch (error) {
    console.error("Error fetching interviews:", error);
    return [];
  }
}

async function populateFilters() {
  const interviews = await fetchAndProcessInterviews();
  if (!interviews || !Array.isArray(interviews)) {
    console.error("Invalid interview data received.");
    return;
  }

  const jobTitlesSet = new Set();
  interviews.forEach((interview) => {
    if (interview.job_title) {
      jobTitlesSet.add(interview.job_title);
    }
  });
  const jobTitles = Array.from(jobTitlesSet).sort();
  const jobSelect = document.getElementById("filter-job");
  const statusSelect = document.getElementById("filter-status");

  // Clear existing job title options (except the "All" option)
  jobSelect.innerHTML = '<option value="">All Job Titles</option>';

  // Populate job titles
  jobTitles.forEach((title) => {
    const option = document.createElement("option");
    option.value = title;
    option.textContent = title;
    jobSelect.appendChild(option);
  });

  // Populate static statuses
  const statuses = ["Scheduled", "Rescheduled", "Canceled"];
  statusSelect.innerHTML = '<option value="">All Statuses</option>';
  statuses.forEach((status) => {
    const option = document.createElement("option");
    option.value = status;
    option.textContent = status;
    statusSelect.appendChild(option);
  });
}

async function initializePage() {
  await populateFilters(); // Populate filters first
  window.interviewData = await fetchAndProcessInterviews(); // Store interviews in window.interviewData
  renderInterviews();
}

// Function to format date for display
function formatDate(dateString) {
  const options = {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  };
  return new Date(dateString).toLocaleDateString("en-US", options);
}

// Function to format time for display
function formatTime(timeString) {
  console.log(" time string is : ", timeString);
  const [hours, minutes] = timeString.split(":");
  let hour = parseInt(hours, 10);
  let period = "AM";

  if (hour === 0) {
    hour = 12; // Midnight
  } else if (hour === 12) {
    period = "PM"; // Noon
  } else if (hour > 12) {
    hour -= 12;
    period = "PM";
  }

  const formattedMinutes = minutes.padStart(2, "0"); // Ensure minutes have leading zero

  return `${hour}:${formattedMinutes} ${period}`;
}
// Function to calculate time remaining
function getTimeRemaining(dateStr, timeStr) {
  const now = new Date();
  const interviewDate = new Date(`${dateStr}T${timeStr}`);

  const diff = interviewDate - now;
  if (diff <= 0) return "Starting now";

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (hours > 0) {
    return `${hours}h ${minutes}m remaining`;
  } else {
    return `${minutes}m remaining`;
  }
}

// Function to create accordion interview item
function createAccordionItem(interview, isToday) {
  const accordionItem = document.createElement("div");
  accordionItem.className = "interview-accordion";
  accordionItem.dataset.id = interview.job_id;
  accordionItem.dataset.candidateId = interview.candidate_id;
  accordionItem.dataset.jobTitle = interview.job_title;
  accordionItem.dataset.candidateEmail = interview.email;
  accordionItem.dataset.candidateName = interview.candidate_name;
  accordionItem.dataset.status = interview.status;

  console.log(" accordionItem.dataset", accordionItem.dataset);
  const statusClass = `status-${interview.status.toLowerCase()}`;

  const timeDisplay = formatTime(interview.time);
  const dateDisplay = formatDate(interview.date);
  console.log(" interview.date : ", dateDisplay, timeDisplay);

  let countdownHtml = "";
  if (isToday && interview.status !== "Canceled") {
    countdownHtml = `<span class="countdown">${getTimeRemaining(
      interview.date,
      interview.time
    )}</span>`;
  }

  // Location or link display
  let locationHtml = "";
  if (interview.mode === "Online") {
    locationHtml = interview.location
      ? `<a href="${interview.location}" target="_blank">Join Meeting</a>`
      : `<div class="not-found" >Not found</p>`;
  } else {
    locationHtml = interview.location
      ? `<a href="${interview.location}" target="_blank">Join Meeting</a>`
      : `<a class="not-found" >Not found</a>`;
  }

  // Create the accordion header
  const accordionHeader = document.createElement("div");
  accordionHeader.className = "accordion-header";
  accordionHeader.innerHTML = `
        <div class="accordion-title">${interview.job_title}</div>
        <span class="interview-status ${statusClass}">${interview.status}</span>
        <div class="accordion-icon"></div>
    `;

  // Create the accordion content
  const accordionContent = document.createElement("div");
  accordionContent.className = "accordion-content";

  // Create the content body
  const accordionBody = document.createElement("div");
  accordionBody.className = "accordion-body";
  accordionBody.innerHTML = `
        <div class="interview-grid">
            <div class="interview-detail">
                <span class="detail-label">Candidate:</span>
                <span class="detail-value">${interview.candidate_name}</span>
            </div>
            <div class="interview-detail">
                <span class="detail-label">Date:</span>
                <span class="detail-value">${dateDisplay}</span>
            </div>
            <div class="interview-detail">
                <span class="detail-label">Time:</span>
                <span class="detail-value">${timeDisplay} ${countdownHtml}</span>
            </div>
            <div class="interview-detail interview-location">
                <span class="detail-label">Location:</span>
                <span class="detail-value">${locationHtml}</span>
            </div>
        </div>
        ${
          interview.status !== "Canceled"
            ? `
        <div class="interview-actions">
            <button class="btn btn-primary reschedule-btn">Reschedule</button>
            <button class="btn btn-danger cancel-btn">Cancel</button>
        </div>
        `
            : ""
        }
    `;

  // Append the body to the content
  accordionContent.appendChild(accordionBody);

  // Append both header and content to the accordion item
  accordionItem.appendChild(accordionHeader);
  accordionItem.appendChild(accordionContent);

  // Add click event handler for the accordion
  accordionHeader.addEventListener("click", function () {
    this.classList.toggle("active");
    const content = this.nextElementSibling;

    if (this.classList.contains("active")) {
      content.style.maxHeight = content.scrollHeight + "px";
    } else {
      content.style.maxHeight = "0px";
    }
  });

  return accordionItem;
}

// Function to display empty state
function displayEmptyState(container, message) {
  container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">📅</div>
            <p class="empty-state-text">${message}</p>
        </div>
    `;
}

initializePage();

// Function to render interviews with accordion
async function renderInterviews() {
  const todayContainer = document.getElementById("today-interviews");
  const upcomingContainer = document.getElementById("upcoming-interviews");

  // Clear containers
  todayContainer.innerHTML = "";
  upcomingContainer.innerHTML = "";

  // Get today's date in YYYY-MM-DD format
  const today = new Date().toISOString().split("T")[0];

  // Filter interviews based on search and filters
  const searchInput = document
    .getElementById("search-input")
    .value.toLowerCase();
  const jobFilter = document.getElementById("filter-job").value;
  const statusFilter = document.getElementById("filter-status").value;
  // const modeFilter = document.getElementById("filter-mode").value;

  // Wait for the Promise to resolve
  const interviews = await window.interviewData;

  if (!interviews || !Array.isArray(interviews)) {
    console.log("interview data is not valid");
    return;
  }

  const filteredInterviews = interviews.filter((interview) => {
    const jobTitle = interview.job_title || ""; // Default to empty string if undefined
    const candidateName = interview.candidate_name || "";

    const matchesSearch =
      jobTitle.toLowerCase().includes(searchInput) ||
      candidateName.toLowerCase().includes(searchInput);

    const matchesJobFilter =
      !jobFilter || interview.job_title.includes(jobFilter);
    const matchesStatusFilter =
      !statusFilter || interview.status === statusFilter;
    // const matchesModeFilter = !modeFilter || interview.mode === modeFilter;

    return (
      matchesSearch && matchesJobFilter && matchesStatusFilter
      // matchesModeFilter
    );
  });

  // Separate today's and upcoming interviews
  const todayInterviews = filteredInterviews.filter(
    (interview) => interview.date === today
  );
  const upcomingInterviews = filteredInterviews.filter(
    (interview) => interview.date > today
  );

  // Render today's interviews
  if (todayInterviews.length > 0) {
    todayInterviews.forEach((interview) => {
      todayContainer.appendChild(createAccordionItem(interview, true));
    });
  } else {
    displayEmptyState(todayContainer, "No interviews scheduled for today.");
  }

  // Render upcoming interviews
  if (upcomingInterviews.length > 0) {
    upcomingInterviews.forEach((interview) => {
      upcomingContainer.appendChild(createAccordionItem(interview, false));
    });
  } else {
    displayEmptyState(upcomingContainer, "No upcoming interviews scheduled.");
  }
}

// Set up search and filter functionality
document
  .getElementById("search-input")
  .addEventListener("input", renderInterviews);
document
  .getElementById("filter-job")
  .addEventListener("change", renderInterviews);
document
  .getElementById("filter-status")
  .addEventListener("change", renderInterviews);
// document
//   .getElementById("filter-mode")
//   .addEventListener("change", renderInterviews);

// Update countdown timers every minute
setInterval(() => {
  const todayAccordions = document.querySelectorAll(
    "#today-interviews .interview-accordion"
  );
  todayAccordions.forEach((accordion) => {
    const interview = interviewData.find((i) => i.id == accordion.dataset.id);
    if (interview && interview.status !== "Canceled") {
      const countdownEl = accordion.querySelector(".countdown");
      if (countdownEl) {
        countdownEl.textContent = getTimeRemaining(
          interview.date,
          interview.time
        );
      }
    }
  });
}, 60000);

// Display today's date
document.getElementById("today-date").textContent = formatDate(
  new Date().toISOString().split("T")[0]
);

// Initial render
renderInterviews();

document.addEventListener("click", function (e) {
  if (e.target.classList.contains("reschedule-btn")) {
    const accordionItem = e.target.closest(".interview-accordion");

    const id = accordionItem.dataset.id;
    const candidateName = accordionItem.dataset.candidateName;
    const candidateEmail = accordionItem.dataset.candidateEmail; // Assuming you add candidateEmail to data attributes
    const candidateId = accordionItem.dataset.candidateId;

    console.log(" candidateName", candidateName);
    console.log(" candidateEmail: ", candidateEmail);
    console.log("candidateId: ", candidateId); // Log candidateId
    console.log(" id: ", id);
    // Open a modal or navigate to reschedule page
    openRescheduleModal(
      e,
      id,
      candidateId,
      candidateName,
      candidateEmail,
      candidateId
    ); // Pass candidateId

    e.stopPropagation(); // Prevent event bubbling
  } else if (e.target.classList.contains("cancel-btn")) {
    const accordionItem = e.target.closest(".interview-accordion");

    const id = accordionItem.dataset.id;
    const candidateId = accordionItem.dataset.candidateId;
    const candidateName = accordionItem.dataset.candidateName;
    const candidateEmail = accordionItem.dataset.candidateEmail;

    console.log("accordionItem:\n", accordionItem);

    console.log("accordionItem.dataset:\n", accordionItem.dataset);

    showConfirmationPopup(
      `Are you sure cancel the interview with ${candidateName}?`,
      () => {
        // User clicked Yes, proceed with cancellation
        cancelInterview(
          id,
          candidateId,
          candidateName,
          candidateEmail,
          candidateId
        );
        window.interviewData = fetchAndProcessInterviews();
        renderInterviews();
      },
      () => {
        // User clicked No, do nothing
        console.log("Cancellation aborted by user.");
      }
    );

    e.stopPropagation(); // Prevent event bubbling
  }
});

function showConfirmationPopup(message, onYes, onNo) {
  // Create the popup container
  const popup = document.createElement("div");
  popup.className = "confirm-popup";

  // Create the popup content
  const popupContent = document.createElement("div");
  popupContent.className = "popup-content";

  // Create the message heading
  const messageHeading = document.createElement("h3");
  messageHeading.textContent = message;
  popupContent.appendChild(messageHeading);

  // Create the action buttons
  const popupActions = document.createElement("div");
  popupActions.className = "popup-actions";

  const yesButton = document.createElement("button");
  yesButton.className = "btn btn-success";
  yesButton.textContent = "Yes";
  yesButton.addEventListener("click", () => {
    if (onYes) {
      onYes();
    }
    document.body.removeChild(popup); // Remove the popup
  });

  const noButton = document.createElement("button");
  noButton.className = "btn btn-danger";
  noButton.textContent = "No";
  noButton.addEventListener("click", () => {
    if (onNo) {
      onNo();
    }
    document.body.removeChild(popup); // Remove the popup
  });

  popupActions.appendChild(yesButton);
  popupActions.appendChild(noButton);
  popupContent.appendChild(popupActions);

  popup.appendChild(popupContent);

  // Append the popup to the body
  document.body.appendChild(popup);
}

function openRescheduleModal(
  event,
  jobId,
  candidateId,
  candidateName,
  candidateEmail
) {
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
        // Create the button and add the listener *only* if it doesn't exist
        scheduleButton = document.createElement("button");
        scheduleButton.textContent = "Schedule Meeting";
        scheduleButton.classList.add("schedule-meeting-btn");
        calendarPopup.appendChild(scheduleButton);

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
                action: "reschedule",
                candidate_id: candidateId,
                candidate_name: candidateName,
                candidate_email: "devradhekrishna1@gmail.com",
                recruiter_email: "yourbestrecruiterai@gmail.com",
                datetime: isoDateTime,
                timezone: userTimezone,
                job_id: jobId,
              }),
            });

            const data = await response.json();
            console.log(
              " ==== <><><> Schedule meeting Api called <><><> ========="
            );
            if (data.success) {
              showPopup("Interview is scheduled successfully!", true); // Success message

              const utcDateTime = luxon.DateTime.fromISO(
                data.scheduled_datetime
              );

              const localDateTime = utcDateTime.toLocaleString(
                luxon.DateTime.DATETIME_MED
              );
              window.interviewData = await fetchAndProcessInterviews();
              renderInterviews();
            } else {
              showPopup("Error: Failed to schedule the interview.", false); // Error message
            }
          } catch (error) {
            console.error("Error scheduling interview:", error);
          } finally {
            showLoadingOverlay(false);

            // Close the calendar popup
            if (fp) {
              fp.close();
            }
          }
        });
      }
    },
  });

  const calendarPopup = document.querySelector(".flatpickr-calendar");
  calendarContainer.appendChild(calendarPopup);
  // Open the calendar popup
  fp.open();
  // Prevent the event from propagating to the document
  event.stopPropagation();
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

let overlay = null;
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

// const outsideClickListener = (event) => {
//   if (
//     !calendarContainer.contains(event.target) &&
//     event.target !== document.querySelector(".date-picker-btn")
//   ) {
//     fp.destroy(); // Destroy Flatpickr instance
//     calendarContainer.remove(); // Remove calendar container
//     document.removeEventListener("click", outsideClickListener);
//   }
// };

// document.addEventListener("click", outsideClickListener);

function showErrorPopup(message) {
  const popup = document.createElement("div");
  popup.classList.add("popup", "popup-error", "show");
  popup.innerHTML = `
                <div class="popup-content">
                    <i class="fas fa-exclamation-triangle popup-icon"></i>
                    <span class="popup-message">${message}</span>
                    <button class="popup-close">Close</button>
                </div>
            `;
  document.body.appendChild(popup);

  popup.querySelector(".popup-close").addEventListener("click", () => {
    popup.remove();
  });
}

function showSuccessPopup(message) {
  const popup = document.createElement("div");
  popup.classList.add("popup", "popup-success", "show");
  popup.innerHTML = `
                <div class="popup-content">
                    <i class="fas fa-check-circle popup-icon"></i>
                    <span class="popup-message">${message}</span>
                    <button class="popup-close">Close</button>
                </div>
            `;
  document.body.appendChild(popup);

  popup.querySelector(".popup-close").addEventListener("click", () => {
    popup.remove();
  });
}

// Function to cancel the interview
async function cancelInterview(id, candidateId, candidateName, candidateEmail) {
  try {
    const response = await fetch("/schedule_meeting", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action: "cancel",
        job_id: id,
        candidate_id: candidateId,
        candidate_name: candidateName,
        candidate_email: "devradhekrishna1@gmail.com",
        recruiter_email: "yourbestrecruiterai@gmail.com",
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    if (result.success) {
      showPopup("Interview is canceled !", true);
      window.interviewData = fetchAndProcessInterviews();
      renderInterviews();
      // Refresh the interviews
    } else {
      showPopup(`Failed to cancel interview: ${result.error}`, false);
    }
  } catch (error) {
    console.error("Error canceling interview:", error);
    showPopup("Failed to cancel interview", false);
  }
}

function showConfirmationPopup(message, onYes, onNo) {
  // Create the popup container
  const popup = document.createElement("div");
  popup.className = "confirm-popup";

  // Create the popup content
  const popupContent = document.createElement("div");
  popupContent.className = "popup-content";

  // Create the message heading
  const messageHeading = document.createElement("h3");
  messageHeading.textContent = message;
  popupContent.appendChild(messageHeading);

  // Create the action buttons
  const popupActions = document.createElement("div");
  popupActions.className = "popup-actions";

  const yesButton = document.createElement("button");
  yesButton.className = "btn btn-success";
  yesButton.textContent = "Yes";
  yesButton.addEventListener("click", () => {
    if (onYes) {
      onYes();
    }
    document.body.removeChild(popup); // Remove the popup
  });

  const noButton = document.createElement("button");
  noButton.className = "btn btn-danger";
  noButton.textContent = "No";
  noButton.addEventListener("click", () => {
    if (onNo) {
      onNo();
    }
    document.body.removeChild(popup); // Remove the popup
  });

  popupActions.appendChild(yesButton);
  popupActions.appendChild(noButton);
  popupContent.appendChild(popupActions);

  popup.appendChild(popupContent);

  // Append the popup to the body
  document.body.appendChild(popup);
}
