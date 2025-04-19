const voicequestions = [
  { text: "What is the name of your company?", start: 0, end: 2 },
  { text: "What is your company's mission statement?", start: 2, end: 5 },
  { text: "What are the core values of your company?", start: 5, end: 8 },
  { text: "What is the job title?", start: 8, end: 10.5 },
  {
    text: "What is the department the role belongs to?",
    start: 10.5,
    end: 14,
  },
  {
    text: "What are the key responsibilities of the role? Be specific and list out the main tasks and duties.",
    start: 14,
    end: 21,
  },
];
let currentVoiceQuestionIndex = 0;
let Voicerecognition;
let qaPair = [];
let silenceTime;
const SILENCE_THRESHOLD = 3000; // 10 seconds in milliseconds
let questionRepeatCount = 0;
const MAX_REPEATS = 1;

// Event Listeners
document.getElementById("startButton").addEventListener("click", function () {
  askNextQuestion();
});

document
  .getElementById("cancelButtonVideo")
  .addEventListener("click", function () {
    if (Voicerecognition) {
      closeVideoPopupAndRedirect();
      Voicerecognition.stop();
    }
    document.getElementById("question").innerText = "Conversation cancelled.";
    document.getElementById("answer").innerText = "";
    currentVoiceQuestionIndex = 0;
  });

// File Upload Functions
function uploadAudio() {
  var file = document.getElementById("audioInput").files[0];
  if (!file) {
    showFloatingMessage("Please choose a file first.");
    return;
  }
  var formData = new FormData();
  formData.append("file", file);
  ajaxCall("/audio-to-text", formData);
}

function uploadPDF() {
  var file = document.getElementById("pdfInput").files[0];
  if (!file) {
    showFloatingMessage("Please choose a file first.");
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
        showFloatingMessage(
          "Error in conversion with status code: " + xhr.status
        );
        $("#loader").hide();
        $("#overlay").hide();
      }
    },
    error: function (xhr) {
      showFloatingMessage("Error in conversion");
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


// Voice Input Functions
function askNextQuestion() {
  if (currentVoiceQuestionIndex < voicequestions.length) {
    const question = voicequestions[currentVoiceQuestionIndex];

    // Show video popup and play the video for the question duration
    const videoPopup = document.getElementById("videoPopup");
    const questionVideo = document.getElementById("questionVideo");
    videoPopup.style.display = "block";
    questionVideo.currentTime = question.start;

    // Add error handling for video playback
    questionVideo.onerror = function () {
      console.error("Video playback error");
      handleVideoError();
    };

    // Ensure video is fully loaded before playing
    questionVideo.oncanplay = function () {
      questionVideo.play().catch(function (error) {
        console.error("Video play error:", error);
        handleVideoError();
      });
    };

    questionVideo.ontimeupdate = function () {
      if (questionVideo.currentTime >= question.end) {
        questionVideo.pause();
        document.getElementById("question").innerText = "Listening...";
        startvoiceListening(question.text);
      }
    };

    // Add a timeout in case the video doesn't trigger the timeupdate event
    setTimeout(function () {
      if (
        questionVideo.paused &&
        currentVoiceQuestionIndex === voicequestions.indexOf(question)
      ) {
        console.log("Video playback timed out");
        handleVideoError();
      }
    }, (question.end - question.start + 2) * 1000); // Add 2 seconds buffer
  } else {
    document.getElementById("answer").innerText = "";
    saveAnswers();
  }
}

function handleVideoError() {
  document.getElementById("question").innerText =
    voicequestions[currentVoiceQuestionIndex].text;
  startvoiceListening(voicequestions[currentVoiceQuestionIndex].text);
}

function startvoiceListening(question) {
  if (Voicerecognition) {
    Voicerecognition.stop();
  }
  Voicerecognition = new (window.SpeechRecognition ||
    window.webkitSpeechRecognition)();
  Voicerecognition.lang = "en-US";
  Voicerecognition.interimResults = true;
  Voicerecognition.continuous = true;

  let finalTranscript = "";
  let isListening = true;
  let hasStartedSpeaking = false;

  Voicerecognition.onresult = async function (event) {
    let interimTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        finalTranscript += event.results[i][0].transcript;
      } else {
        interimTranscript += event.results[i][0].transcript;
      }
    }

    // Reset the silence timer whenever we get a result
    resetSilenceTimer();

    // Set flag to indicate user has started speaking
    hasStartedSpeaking = true;
  };

  Voicerecognition.onend = function () {
    if (isListening) {
      Voicerecognition.start();
    }
  };

  Voicerecognition.onerror = function (event) {
    console.error("Speech Voicerecognition error:", event.error);
    document.getElementById("answer").innerText =
      "Sorry, I could not understand the audio. Please try again.";
    isListening = false;
    processAnswer(finalTranscript);
  };

  function resetSilenceTimer() {
    clearTimeout(silenceTime);
    silenceTime = setTimeout(() => {
      isListening = false;
      Voicerecognition.stop();
      if (hasStartedSpeaking) {
        processAnswer(finalTranscript);
      } else {
        noResponsehandler();
      }
    }, SILENCE_THRESHOLD);
  }

  resetSilenceTimer();

  function noResponsehandler() {
    if (questionRepeatCount < MAX_REPEATS) {
      questionRepeatCount++;
      document.getElementById("answer").innerText =
        "No response detected. Repeating the question.";
      setTimeout(() => {
        askNextQuestion();
      }, 2000);
    } else {
      document.getElementById("answer").innerText =
        "No response detected. Moving to the next question.";
      questionRepeatCount = 0;
      currentVoiceQuestionIndex++;
      setTimeout(() => {
        askNextQuestion();
      }, 2000);
    }
  }

  function processAnswer(answer) {
    questionRepeatCount = 0; // Reset repeat count for next question
    if (answer.toLowerCase().includes("skip")) {
      document.getElementById("answer").innerText = "Question skipped.";
      if (currentVoiceQuestionIndex < voicequestions.length - 1) {
        currentVoiceQuestionIndex++;
        setTimeout(askNextQuestion, 2000);
      } else {
        saveAnswers();
      }
    } else if (answer.toLowerCase().includes("repeat")) {
      document.getElementById("answer").innerText = "Repeating question...";
      setTimeout(askNextQuestion, 2000);
    } else {
      qaPair.push(`Question: ${question}\nAnswer: ${answer}`);
      currentVoiceQuestionIndex++;
      setTimeout(askNextQuestion, 2000);
    }
  }
}

function saveAnswers() {
  console.log("qaPair in save function: ", qaPair);
  text = qaPair
    .map((pair) => `Question: ${pair.question}\nAnswer: ${pair.answer}`)
    .join("\n\n");
  fetch("/save-text", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text: text }),
  })
    .then((response) => response.json())
    .then((data) => {
      closeAIChat(); // Close the popup
      window.location.href = "/process";
      $.ajax({
        url: "/save-resumes-embedding",
        type: "GET",
        success: function (response) {
          console.log("Embeddings saved successfully");
        },
        error: function () {
          console.error("Error saving embeddings");
        },
      });
      console.log("Success:", data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
}

function closeVideoPopupAndRedirect() {
  const videoPopup = document.getElementById("videoPopup");
  videoPopup.style.display = "none";
  window.location.href = "/";
}

// Handle the runtime.lastError (if using Chrome extensions)
if (typeof chrome !== "undefined" && chrome.runtime) {
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (chrome.runtime.lastError) {
      console.error("runtime.lastError:", chrome.runtime.lastError.message);
      sendResponse({
        success: false,
        error: chrome.runtime.lastError.message,
      });
      return true; // Indicate an asynchronous response
    }
    sendResponse({ success: true });
    return true; // Indicate an asynchronous response
  });
}
