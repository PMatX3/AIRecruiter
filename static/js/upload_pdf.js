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
      toastr.error("Please upload a valid file", xhr);
      $("#loader").hide();
      $("#overlay").hide();
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
