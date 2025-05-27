document.addEventListener("DOMContentLoaded", async function () {
  // Cache DOM elements
  const nameField = document.getElementById("name");
  const emailField = document.getElementById("email");
  const linkedinField = document.getElementById("linkedin_email");
  const phoneField = document.getElementById("phone");
  const companyField = document.getElementById("company");
  const countryField = document.getElementById("country");
  const editBtn = document.querySelector(".edit-btn");
  const saveBtn = document.querySelector(".save-btn");

  document.querySelector(".save-btn").addEventListener("click", saveProfile);
  document.querySelector(".edit-btn").addEventListener("click", enableEditMode);

  try {
    const [profileResponse] = await Promise.all([
      fetch("/profile", { headers: { "X-Requested-With": "XMLHttpRequest" } }),
    ]);

    if (!profileResponse.ok) throw new Error("Failed to fetch profile data");

    const profileData = await profileResponse.json();
    populateProfile(profileData);
  } catch (error) {
    console.error("Error fetching profile data:", error);
  }

  // ✅ Ensure is_superadmin is passed to updateTrialTimer
  function populateProfile(data) {
    nameField.value = data.username || "Not available";
    emailField.value = data.email || "Not available";
    phoneField.value = data.phone || "Not available";
    companyField.value = data.company || "Not available";
    countryField.value = data.country || "Not available";
    linkedinField.value = data.linkedin_email || "Not available";
  }

  function openCity(evt, cityName) {
    var i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
      tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
      tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(cityName).style.display = "block";
    evt.currentTarget.className += " active";
  }

  function enableEditMode() {
    document.querySelectorAll(".form-container input").forEach((input) => {
      if (input.id !== "email") input.disabled = false;
    });
    editBtn.disabled = true;
    saveBtn.disabled = false;
  }

  async function saveProfile() {
    console.log(" sAVE PROFILE CALLED ");
    // Trim input values
    let username = nameField.value.trim();
    let phone = phoneField.value.trim();
    let company = companyField.value.trim();
    let country = countryField.value.trim() || null;

    // **Validation Rules**
    // Username: Alphanumeric, not empty, max 30 chars
    if (!/^[a-zA-Z0-9]{1,30}$/.test(username)) {
      toastr.error("Invalid username.");
      return;
    }

    // Phone: Only digits, exactly 10 characters
    phone = phone.replace(/\D/g, ""); // Remove non-numeric characters
    if (phone.length !== 10) {
      toastr.error("Invalid phone. must be exactly 10 digits.");
      return;
    }

    // Company Name: Not empty, no spaces-only input
    if (!company || company.trim().length === 0) {
      toastr.error("Company name cannot be empty.");
      return;
    }

    const countrySelect = document.getElementById("country");

    // Fetch country data from an API
    fetch("https://restcountries.com/v3.1/all") // Example API
      .then((response) => response.json())
      .then((data) => {
        data.forEach((country) => {
          const option = document.createElement("option");
          option.value = country.cca2; // Country code
          option.textContent = country.name.common; // Country name
          countrySelect.appendChild(option);
        });
      })
      .catch((error) => console.error("Error fetching country data:", error));

    // Prepare the profile data
    const profileData = { username, phone, company, country };

    try {
      const response = await fetch("/update-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileData),
      });

      const result = await response.json();
      if (response.status === 200) {
        console.log(" TOSTER EXECUTED");
        toastr.success("Profile updated successfully!");

        disableEditMode();
      } else {
        toastr.error(result.error || "Failed to update profile.");
      }
    } catch (error) {
      toastr.error("An error occurred. Please try again.");
      console.error("Error updating profile:", error);
    }
  }

  function disableEditMode() {
    document
      .querySelectorAll(".form-container input")
      .forEach((input) => (input.disabled = true));
    editBtn.disabled = false;
    saveBtn.disabled = true;
  }
});
