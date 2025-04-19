// navbar.js - Include this in your JavaScript files or in a <script> tag
document.addEventListener("DOMContentLoaded", function () {
  function toggleNotifications(event) {
    event.stopPropagation();
    const notificationPopup = document.getElementById("notification-popup");

    // Check if the popup is already open
    if (notificationPopup.style.display === "block") {
      notificationPopup.style.display = "none"; // Close the popup if it's open
      return; // Exit the function to prevent re-fetching notifications
    }

    fetch("/get_notifications")
      .then((response) => response.json())
      .then((data) => {
        notificationCount = data.count;
        updateNotificationBadge(notificationCount);
        notificationPopup.innerHTML = ""; // Clear old notifications

        if (data.length === 0) {
          notificationPopup.innerHTML =
            "<p class='notification-empty'>No new notifications</p>";
        } else {
          data.forEach((notification) => {
            let div = document.createElement("div");
            // Assuming notification.interview_time is in "HH:mm" format
            const timeParts = notification.interview_time.split(":");
            const hours = parseInt(timeParts[0], 10);
            const minutes = parseInt(timeParts[1], 10);

            // Create a new Date object for today at the specified time
            const now = new Date();
            const utcDate = new Date(
              Date.UTC(
                now.getUTCFullYear(),
                now.getUTCMonth(),
                now.getUTCDate(),
                hours,
                minutes
              )
            );

            // Convert to local time
            const localTime = utcDate.toLocaleTimeString(); // You can customize this as needed

            div.classList.add("notification-item");
            div.innerHTML = `
                        <strong><span class="job-title">Job: ${notification.job_title}</span></strong><br>
                        <span class="candidate-name">${notification.candidate_name}</span>
                        <span class="interview-time">${localTime}</span>
                        
                    `;
            notificationPopup.appendChild(div);
          });

          // Update notification badge
          document.getElementById("notification-count").innerText = data.length;
        }

        notificationPopup.style.display = "block";

        let timeoutId;

        function outsideClickListener(event) {
          // Check if the click was outside the notification popup
          if (notificationPopup && !notificationPopup.contains(event.target)) {
            closePopup(); // Call closePopup if clicked outside
          }
        }

        function closePopup() {
          notificationPopup.style.display = "none";
          document.removeEventListener("click", outsideClickListener); // Remove the outside click listener
          clearTimeout(timeoutId); // Clear the timeout
        }

        timeoutId = setTimeout(closePopup, 3000);

        notificationPopup.addEventListener("mouseover", () => {
          clearTimeout(timeoutId); // Clear the timeout if mouse is over the popup
        });
        notificationPopup.addEventListener("mouseout", () => {
          timeoutId = setTimeout(closePopup, 3000); // Reset the timeout when mouse leaves the popup
        });
      });

    // Close when clicking outside
    document.addEventListener("click", function closePopup(e) {
      if (!e.target.closest(".notification-container")) {
        notificationPopup.style.display = "none";
        document.removeEventListener("click", closePopup);
      }
    });
  }

  // Toggle dropdown menu
  const menuBtn = document.getElementById("menu-btn");
  const dropdownMenu = document.getElementById("dropdown-menu");

  menuBtn.addEventListener("click", function (e) {
    e.stopPropagation();

    // Close notifications popup if open
    notificationPopup.style.display = "none";

    // Toggle dropdown menu
    dropdownMenu.style.display =
      dropdownMenu.style.display === "block" ? "none" : "block";
  });

  // Close popups when clicking outside
  document.addEventListener("click", function () {
    notificationPopup.style.display = "none";
    dropdownMenu.style.display = "none";
  });

  // Logout functionality
  document.getElementById("logout-btn").addEventListener("click", function (e) {
    e.preventDefault();
    // Add your logout logic here
    console.log("Logging out...");
    // Example: redirect to login page
    // window.location.href = '/login';
  });

  // Highlight active navigation item based on current page
  const currentPage = window.location.pathname;
  const navLinks = document.querySelectorAll(".nav-link");

  navLinks.forEach((link) => {
    const linkPath = link.getAttribute("href");
    if (currentPage === linkPath || currentPage.startsWith(linkPath)) {
      link.classList.add("active");
    }
  });
});
