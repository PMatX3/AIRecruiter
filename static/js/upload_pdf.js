toastr.options = {
  closeButton: false,
  debug: false,
  newestOnTop: false,
  progressBar: true, // Show a progress bar
  preventDuplicates: false,
  positionClass: "toast-top-right", // Adjust position as needed
  onclick: null,
  showDuration: "300",
  hideDuration: "1000",
  timeOut: "3000", // Duration toast is shown
  extendedTimeOut: "1000",
  showEasing: "swing",
  hideEasing: "linear",
  showMethod: "fadeIn",
  hideMethod: "fadeOut",
};

function uploadPDF() {
  var file = document.getElementById("pdfInput").files[0];
  if (!file) {
    toastr.error("Please upload job description to proceed");
    return;
  }
  var formData = new FormData();
  console.log("file: ", file);
  formData.append("file", file);
  console.log("formData: ", formData);
  ajaxCall("/pdf-to-text", formData);
}

function ajaxCall(url, formData) {
  $("#overlay").show();
  $("#loader").show();
  $.ajax({
    url: url,
    type: "POST",
    data: formData,
    contentType: false,
    processData: false,
    timeout: 60000,
    success: function (data, textStatus, xhr) {
      if (xhr.status === 200) {
        $("#loader").hide();
        $("#overlay").hide();
        window.location.href = "/process";
        $.ajax({
          url: "/save-resumes-embedding",
          type: "GET",
          success: function (response) {
            // Handle success if needed
          },
          error: function () {
            // Handle errors if the request fails
          },
        });
      } else {
        toastr.error("Error in conversion with status code: " + xhr.status);
        $("#loader").hide();
        $("#overlay").hide();
      }
    },
    error: function (xhr) {
      $("#loader").hide();
      $("#overlay").hide();

      let errorMsg = "An error occurred while uploading the file.";
      try {
        const response = JSON.parse(xhr.responseText);

        if (response.linkedin_required) {
          // Show LinkedIn popup
          document.getElementById("linkedinModal").classList.remove("hidden");

          // Handle button events
          document.getElementById("linkedinYesBtn").onclick = function () {
            window.location.href = "/login-linkedin";
          };

          document.getElementById("linkedinNoBtn").onclick = function () {
            document.getElementById("linkedinModal").classList.add("hidden");
          };

          return;
        }

        if (response.error) {
          errorMsg = response.error;
        }
      } catch (err) {
        console.error("Failed to parse error JSON", err);
      }

      alert(errorMsg); // Optional fallback
    },
  });
}

function showFloatingMessage(message) {
  const floatingMessage = $('<div class="floating-message"></div>').text(
    message
  );
  $("body").append(floatingMessage);
  setTimeout(function () {
    floatingMessage.remove();
  }, 3000);
}
