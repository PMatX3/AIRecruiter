document.addEventListener("DOMContentLoaded", function () {
  let timeoutId;
  const mobileMenuBtn = document.getElementById("mobile-menu-toggle");
  const nav = document.getElementById("main-nav");
  const userDropdown = document.getElementById("user-dropdown");

  let notificationCounting;
  let isSuperadmin;
  const notificationPopup = document.getElementById("notification-popup");
  const notificationCount = document.getElementById("notification-count");

  function updateNavbarData() {
    fetch("/notifications_update")
      .then((response) => response.json())
      .then((data) => {
        notificationCounting = data.notification_count;
        const isSuperadmin = data.is_superadmin;
        if (isSuperadmin) {
          document.getElementById("trial-timer").innerHTML =
            "<span>Welcome Super Admin!</span>"; // Super Admin UI
          document.getElementById("upgrade-plann-btn").style.display = "none";
        }
        console.log(" Navbar data updated:", data);

        updateNotificationBadge({ count: notificationCounting });
      })
      .catch((error) => {
        console.error("Error fetching navbar data:", error);
      });
  }

  // Initial call to update data
  updateNavbarData();

  // Call updateNavbarData at an interval if needed.

  // Toggle mobile menu
  mobileMenuBtn.addEventListener("click", () => {
    nav.classList.toggle("active");
    mobileMenuBtn.classList.toggle("active");

    // Reset dropdown when closing menu
    if (!nav.classList.contains("active")) {
      userDropdown.classList.remove("active");
    }
  });

  // Handle dropdown on mobile
  if (window.innerWidth <= 920) {
    userDropdown
      .querySelector(".dropdown-icon")
      .addEventListener("click", function (e) {
        e.preventDefault();
        userDropdown.classList.toggle("active");
      });
  }

  // Close menu when clicking outside
  document.addEventListener("click", function (e) {
    const isNavClick = nav.contains(e.target);
    const isMenuBtnClick = mobileMenuBtn.contains(e.target);

    if (
      !isNavClick &&
      !isMenuBtnClick &&
      nav.classList.contains("active") &&
      window.innerWidth <= 920
    ) {
      nav.classList.remove("active");
      mobileMenuBtn.classList.remove("active");
      userDropdown.classList.remove("active");
    }
  });

  // Handle window resize
  window.addEventListener("resize", function () {
    if (window.innerWidth > 920 && nav.classList.contains("active")) {
      nav.classList.remove("active");
      mobileMenuBtn.classList.remove("active");
    }

    // Rebind dropdown event on resize
    if (window.innerWidth <= 920) {
      userDropdown
        .querySelector(".dropdown-icon")
        .addEventListener("click", function (e) {
          e.preventDefault();
          userDropdown.classList.toggle("active");
        });
    }
  });

  window.toggleNotifications = function (event) {
    event.stopPropagation(); // Prevents closing when clicking the button

    // Check if the popup is already open
    if (notificationPopup.style.display === "block") {
      closePopup();
      return;
    }

    fetch("/get_notifications")
      .then((response) => response.json())
      .then((data) => {
        let notifications = data.notifications; // Ensure it's an array
        console.log(" notification s:  ", notifications);
        updateNotificationBadge(data.count); // Update badge count

        notificationPopup.innerHTML = ""; // Clear old notifications

        if (data.length === 0) {
          notificationPopup.innerHTML =
            "<p class='notification-empty'>No new notifications</p>";
        } else {
          data.forEach((notification) => {
            let div = document.createElement("div");
            div.classList.add("notification-item");

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
            const localTime = utcDate.toLocaleTimeString();

            div.innerHTML = `
                                  </strong>
                                  <strong><span class="candidate-name">${notification.candidate_name}</span><br>
                                  <span class="job-title">Job: ${notification.job_title}</span>
                                  <span class="interview-time">${localTime}</span>
                              `;
            notificationPopup.appendChild(div);
          });
        }

        // Update notification badge
        document.getElementById("notification-count").innerText = data.length;

        // Show the popup
        notificationPopup.style.display = "block";

        // Set auto-close timeout
        timeoutId = setTimeout(closePopup, 3000);
      });

    // Close when clicking outside
    document.addEventListener("click", outsideClickListener);
  };

  // Function to close the popup
  function closePopup() {
    notificationPopup.style.display = "none";
    clearTimeout(timeoutId); // Clear timeout
    document.removeEventListener("click", outsideClickListener);
  }

  // Function to detect outside clicks
  function outsideClickListener(event) {
    if (
      !event.target.closest(".notification-container") &&
      !event.target.closest("#notification-popup")
    ) {
      closePopup();
    }
  }

  // Prevent auto-close when hovering
  notificationPopup.addEventListener("mouseover", () =>
    clearTimeout(timeoutId)
  );
  notificationPopup.addEventListener(
    "mouseout",
    () => (timeoutId = setTimeout(closePopup, 3000))
  );

  function updateNotificationBadge(count) {
    const badge = document.getElementById("notification-count");
    if (count == 0) {
      badge.style.display = "none";
    } else {
      badge.textContent = count;
    }
  }

  const dropdownMenu = document.getElementById("dropdown-menu");
  const dropdownContent = userDropdown.querySelector(".dropdown-content"); // Get the dropdown content div

  dropdownMenu.addEventListener("click", function (event) {
    event.stopPropagation(); // Prevent the click from immediately closing the dropdown

    // Toggle the visibility of the dropdown content
    if (dropdownContent.style.display === "block") {
      dropdownContent.style.display = "none";
    } else {
      dropdownContent.style.display = "block";
    }
  });

  // Close the dropdown when clicking outside
  document.addEventListener("click", function (event) {
    if (!userDropdown.contains(event.target)) {
      dropdownContent.style.display = "none";
    }
  });

  function handleLogout(event) {
    event.preventDefault(); // Prevent default link behavior
    Swal.fire({
      // Assuming you are using sweet alert, if not change accordingly
      title: "Are you sure?",
      text: "You will be logged out!",
      icon: "warning",
      showCancelButton: true,
      confirmButtonColor: "#d33",
      cancelButtonColor: "#3085d6",
      confirmButtonText: "Yes, logout!",
    }).then((result) => {
      if (result.isConfirmed) {
        window.location.href = "/logout"; // Redirect to logout
      }
    });
  }

  // Add click event listener to the profile link
  userDropdown
    .querySelector('a[href="/profile"]')
    .addEventListener("click", function (event) {
      event.preventDefault(); // Prevent default link behavior
      window.location.href = "/profile"; // Navigate to the profile page.
    });
});
