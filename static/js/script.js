const GEMINI_API_KEY = CONFIG.GEMINI_API_KEY;
const GEMINI_API_ENDPOINT =
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent";

const OPENAI_API_KEY = CONFIG.OPENAI_API_KEY;

const chatOutput = document.getElementById("chat-output");
const voiceBtn = document.getElementById("voice-btn");
const status = document.getElementById("status");

let recognition = null;
let currentQuestionIndex = 0;
let retryCount = 0;
let responseBuffer = "";
let silenceTimer = null;
let processingResponse = false;
let qaPairs = [];
const MAX_RETRIES = 2;
const SILENCE_TIMEOUT = 3000;
let mediaRecorder = null;

let isSpeaking = false;
let isListening = false;
let isProcessing = false;
let isRecording = false;
let isSilent = false;
let isError = false;

const questions = [
  "Hello there! I hope you're having a wonderful day, What is the job title or position you want to be filled?",
  "Great! What does your ideal candidate for this role look like?",
  "Good answer!, What are the three most important characteristics or qualities you're looking for in the person filling this role?",
  "Nice!, What are the main responsibilities for this position?",
  "What specific experiences are required or highly valued for the role?",
  " Can you briefly describe the work environment?",
  "Great to know! Can you describe the company culture in a few sentences?",
  " Is there a clear career progression or growth path for the candidates in this role?",
  " What is the ideal starting date for this position?",
  " What is the salary range for the role?",
  "Are there any specific skills or qualifications the candidate must have?",
  "Is the role hybrid? If so, how many days per week will the person be required to be in the office?",
  "What are the key performance targets or milestones for the person in this role?",
];

let interviewData = {
  timestamp: new Date().toISOString(),
  responses: {},
  chatHistory: [], // To store the entire chat
};

let chatHistory = [];
let selectedVoice = null;
const synth = window.speechSynthesis;

async function initializeVoice() {
  return new Promise((resolve) => {
    function setVoice() {
      const voices = speechSynthesis.getVoices();

      if (voices.length === 0) {
        console.warn("No voices available yet.");
        return;
      }

      // Try to get Google US English voice
      let selectedVoice =
        voices.find((voice) => voice.name === "Google US English") ||
        voices.find(
          (voice) => voice.name.includes("Google") && voice.lang === "en-US"
        ) ||
        voices.find((voice) => voice.lang === "en-US") ||
        voices[0];

      console.log(" Selected voice is : ", selectedVoice);
      if (!selectedVoice) {
        selectedVoice =
          voices.find((voice) => voice.name.includes("Microsoft Zira")) ||
          voices.find((voice) => voice.name.includes("Samantha")) ||
          voices.find(
            (voice) =>
              voice.lang.startsWith("en") &&
              voice.name.toLowerCase().includes("female")
          ) ||
          voices.find((voice) => voice.lang.startsWith("en")) ||
          voices[0];
      }

      if (!selectedVoice) {
        selectedVoice = voices.find((voice) => voice.name.includes("Samantha"));
      }

      if (!selectedVoice) {
        selectedVoice =
          voices.find(
            (voice) =>
              voice.lang.startsWith("en") &&
              voice.name.toLowerCase().includes("female")
          ) ||
          voices.find((voice) => voice.lang.startsWith("en")) ||
          voices[0];
      }

      console.log("Selected voice:", selectedVoice?.name);
      resolve(selectedVoice);
    }

    // Chrome loads voices asynchronously
    if (speechSynthesis.onvoiceschanged !== undefined) {
      speechSynthesis.onvoiceschanged = () => setTimeout(setVoice, 100);
    }

    // For browsers that load voices synchronously
    setTimeout(() => {
      const voices = speechSynthesis.getVoices();
      if (voices.length > 0) {
        setVoice();
      }
    }, 200);
  });
}

async function speak(text) {
  if (isSpeaking) {
    console.log("Already speaking, queuing:", text);
    return new Promise((resolve) => {
      const queuedSpeak = async () => {
        document.getElementById("status").textContent = "Speaking...";
        await speak(text);
        resolve();
      };
      setTimeout(queuedSpeak, 500); // Delay before checking again
    });
  }
  isSpeaking = true;

  const synth = window.speechSynthesis;

  if (!selectedVoice) {
    selectedVoice = await initializeVoice();
  }

  console.log(" speak-text : ", text);
  return new Promise((resolve) => {
    synth.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    if (selectedVoice) {
      utterance.voice = selectedVoice;
    } else {
      console.warn("No voice selected. Using default.");
    }

    utterance.rate = 0.8; // Set to normal speaking rate
    utterance.pitch = 1.0; // Set to normal pitch
    utterance.volume = 1; // Set volume to maximum

    if (text.trim().endsWith("?")) {
      utterance.pitch = 1.2; // Increase pitch for questions
      utterance.rate = 0.9; // Optionally, you can slightly increase the rate for questions
    }

    // Event listeners for handling end and error
    utterance.onend = () => {
      console.log("speech ended.");
      isSpeaking = false;
      resolve();
    };
    utterance.onerror = (event) => {
      console.error("An error occurred while speaking:", event.error);
      isSpeaking = false;
      resolve();
    };

    // Speak the utterance
    synth.speak(utterance);

    // Keep alive fix for mobile devices
    if (window.platform === "iOS" || window.platform === "Android") {
      const preventSleep = setInterval(() => {
        if (!synth.speaking) {
          clearInterval(preventSleep);
          return;
        }
        synth.pause();
        synth.resume();
      }, 14000);
    }

    addMessage(text, false);
  });
}

const preloadImage = new Image();
preloadImage.src = "static/images/grediant.jpg";
preloadImage.onload = function () {
  document.querySelector(
    ".chat-container"
  ).style.backgroundImage = `url(${preloadImage.src})`;

  // Create and center the animation element
};

const chatContainer = document.querySelector(".chat-container");
if (!chatContainer) {
  console.error("Chat container element not found!");
}

const animationContainer = document.createElement("div"); // Create a div for the animation
animationContainer.id = "lottie-animation"; // Give it an ID
animationContainer.style.position = "absolute"; // Absolute positioning for centering
animationContainer.style.top = "50%";
animationContainer.style.left = "50%";
animationContainer.style.transform = "translate(-50%, -50%)"; // Center it
chatContainer.appendChild(animationContainer); // Add to the container

// Load the Lottie animation
lottie.loadAnimation({
  container: animationContainer,
  renderer: "svg", // or 'canvas'
  loop: true,
  autoplay: true,
  path: "static/videos/pinkwaves.json", // Path to your Lottie JSON file
});

function openAIChat() {
  document.getElementById("aiChatPopup").style.display = "block";
  document.getElementById("overlay").style.display = "block";
  // Reset chat
  voiceChatQuestionIndex = 0;
  voiceChatHistory = [];
  qaPairs = [];
  document.getElementById("chat-output").innerHTML = "";
  document.getElementById("voice-btn").disabled = false;
}

async function addMessage(text, isUser) {
  if (!isUser) {
    // Create and add typing indicator
    const typingContainer = document.createElement("div");
    typingContainer.className = "bot-typing-container";

    const typingDiv = document.createElement("div");
    typingDiv.className = "typing";

    for (let i = 0; i < 3; i++) {
      const span = document.createElement("span");
      typingDiv.appendChild(span);
    }

    typingContainer.appendChild(typingDiv);
    chatOutput.appendChild(typingContainer);
    chatOutput.scrollTop = chatOutput.scrollHeight;

    // Wait for a short duration to show typing effect
    await new Promise((resolve) => setTimeout(resolve, 800));

    // Remove typing indicator
    chatOutput.removeChild(typingContainer);
  }

  const div = document.createElement("div");
  div.className = `message chat-bubble ${
    isUser ? "user-message" : "bot-message"
  }`;
  div.textContent = text;
  chatOutput.appendChild(div);
  chatOutput.scrollTop = chatOutput.scrollHeight;
  setTimeout(() => div.classList.add("visible"), 100);

  if (!isUser) {
    // If the message is from the bot, store it as a question
    interviewData.chatHistory.push({ question: text, answer: "" });
  } else {
    // If the message is from the user, store it as an answer
    if (
      interviewData.chatHistory.length > 0 &&
      interviewData.chatHistory[interviewData.chatHistory.length - 1].question
    ) {
      // Add the answer to the last question
      interviewData.chatHistory[interviewData.chatHistory.length - 1].answer =
        text;
    }
  }
}

async function handleNoResponse() {
  try {
    if (retryCount < MAX_RETRIES) {
      retryCount++;
      await speak("I didn't hear your response. Let me repeat the question.");
      await askCurrentQuestion();
    } else {
      await endInterview(
        "No response received after multiple attempts. Ending conversation."
      );
    }
  } finally {
    isProcessing = false;
  }
}

async function askCurrentQuestion() {
  if (isProcessing) return;
  isProcessing = true;
  try {
    if (currentQuestionIndex < questions.length) {
      status.textContent = "Speaking question...";
      await speak(questions[currentQuestionIndex]);
      startListening();
    }
  } finally {
    isProcessing = false;
    status.textContent = "";
  }
}

// // system Defult Listning Method
// function startListening() {
//   if (recognition) recognition.stop();

//   recognition = new (window.SpeechRecognition ||
//     window.webkitSpeechRecognition)();
//   recognition.continuous = true;
//   recognition.interimResults = true;
//   recognition.lang = "en-US";
//   responseBuffer = "";
//   status.textContent = "Listening...";
//   isListening = true; // Set listening flag to true

//   silenceTimer = setTimeout(() => handleNoResponse(), 15000);

//   recognition.onresult = (event) => {
//     clearTimeout(silenceTimer);
//     let interim = "";
//     let final = "";

//     for (let i = event.resultIndex; i < event.results.length; i++) {
//       const transcript = event.results[i][0].transcript;
//       if (event.results[i].isFinal) {
//         final += transcript + " ";
//         responseBuffer += transcript + " ";
//       } else {
//         interim += transcript;
//       }
//     }

//     status.textContent = interim ? "Listening: " + interim : "Listening...";

//     // Reset silence timer when user speaks
//     silenceTimer = setTimeout(() => {
//       if (responseBuffer.trim()) {
//         addMessage(responseBuffer.trim(), true);
//         processUserResponse(responseBuffer.trim());
//       }
//       // } else {
//       //   console.log("156 handleNoResponse");
//       //   handleNoResponse();
//       // }
//     }, SILENCE_TIMEOUT);
//   };

//   recognition.onend = () => {
//     if (!recognition) {
//       return;
//     }
//   };

//   recognition.onerror = (event) => {
//     clearTimeout(silenceTimer);
//     console.log(" Error type: :  ", event.error)
//     if (event.error === "no-speech") {
//       startListening();
//     } else if(event.error === "network"){
//       endInterview("Network error encountered. Please try using a different browser to continue.");
//     }

//   };

//   try {
//     recognition.start();
//   } catch (error) {
//     console.error("Error starting recognition:", error);
//     endInterview("Failed to start speech recognition.");
//   }
// }
// // system Defult stopListning Method
// function stopListening() {
//   if (!isListening) return;
//   isListening = false;

//   if (synth && synth.speaking) {
//     synth.cancel(); // Stops all utterances
//   }
//   if (recognition) {
//     recognition.stop();
//     recognition.onend = null;
//     recognition.onerror = null;
//     recognition.onresult = null;
//   }
//   clearTimeout(silenceTimer);
//   voiceBtn.disabled = false;
//   status.textContent = "";

//   closeAIChat();
// }

class AudioVisualizer {
  constructor(container, barCount = 15) {
    this.container =
      typeof container === "string"
        ? document.querySelector(container)
        : container;
    this.barCount = barCount;
    this.analyser = null;
    this.dataArray = null;
    this.animationId = null;
    this.isListening = false;

    this.init();
  }

  init() {
    // Clear the container
    this.container.innerHTML = "";
    this.container.style.display = "flex";
    this.container.style.flexDirection = "row";
    this.container.style.alignItems = "center";
    this.container.style.justifyContent = "center";
    this.container.style.padding = "0";
    this.container.style.height = "20px"; // Reduced overall height

    // Create status text
    this.statusText = document.createElement("div");
    this.statusText.className = "status-text";
    this.statusText.style.fontStyle = "italic";
    this.statusText.style.color = "white";
    this.statusText.style.marginRight = "10px";
    this.statusText.textContent = "Listening...";
    this.container.appendChild(this.statusText);

    // Create bars container
    this.barsContainer = document.createElement("div");
    this.barsContainer.className = "audio-bars";
    this.barsContainer.style.display = "flex";
    this.barsContainer.style.alignItems = "center";
    this.barsContainer.style.justifyContent = "center";
    this.barsContainer.style.height = "30px"; // Reduced height
    this.container.appendChild(this.barsContainer);

    // Create the wave bars
    this.bars = [];
    for (let i = 0; i < this.barCount; i++) {
      const bar = document.createElement("div");
      bar.className = "audio-bar";
      bar.style.width = "2px";
      bar.style.backgroundColor = "blue";
      bar.style.borderRadius = "1px";
      bar.style.height = "10px"; // Starting with smaller bars
      bar.style.marginLeft = "2px";
      bar.style.transition = "height 0.1s ease";
      this.barsContainer.appendChild(bar);
      this.bars.push(bar);
    }
  }

  connect(analyser) {
    this.analyser = analyser;
    this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.isListening = true;
    this.setStatus("Listening...");
    this.animate();
  }

  animate() {
    if (!this.isListening) return;

    this.analyser.getByteFrequencyData(this.dataArray);

    // Update the bars with limited height
    for (let i = 0; i < this.barCount; i++) {
      // Use a subset of the frequency data for each bar
      const index = Math.floor(i * (this.dataArray.length / this.barCount));
      const value = this.dataArray[index];

      // Limit maximum height to 10px regardless of volume
      // Add small random variation for natural movement
      const randomFactor = Math.random() * 0.3 + 0.7;
      const maxHeight = 50; // Maximum height in pixels
      const normalizedValue = value / 255; // Normalize to 0-1 range
      const height = Math.max(
        3,
        Math.min(maxHeight, normalizedValue * maxHeight * randomFactor)
      );

      this.bars[i].style.height = `${height}px`;
    }

    this.animationId = requestAnimationFrame(() => this.animate());
  }

  setStatus(text) {
    this.statusText.textContent = text;

    // If processing, hide the bars
    if (text === "Processing...") {
      this.barsContainer.style.opacity = "0.5";
    } else {
      this.barsContainer.style.opacity = "1";
    }
  }

  stop() {
    this.isListening = false;
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }

    // Reset all bars to minimum height
    this.bars.forEach((bar) => {
      bar.style.height = "3px";
    });
  }
}

function startListening() {
  if (mediaRecorder) {
    mediaRecorder.stop();
    mediaRecorder = null;
  }
  startRecording();
  silenceTimer = 3000;
}

function stopListening() {
  if (!isListening) return;
  isListening = false;

  if (synth && synth.speaking) {
    synth.cancel();
  }
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach((track) => track.stop());
  }
  clearTimeout(silenceTimer);
  voiceBtn.disabled = false;
  status.textContent = "";

  closeAIChat();
}

async function startRecording() {
  if (isRecording) {
    console.log("Already recording, ignoring request.");
    return;
  }
  isRecording = true;

  console.log("Recording started");

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        sampleRate: 16000,
        sampleSize: 16,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,

        latency: 0,

        advanced: [
          {
            echoCancellation: { exact: true },
            noiseSuppression: { exact: true },
            autoGainControl: { exact: true },
          },
        ],
      },
    });

    // Create audio context and analyzer for visualization
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const microphone = audioContext.createMediaStreamSource(stream);

    // Additional audio processing for better noise handling
    const gainNode = audioContext.createGain();
    gainNode.gain.value = 1.2; // Boost the input signal slightly

    // Create a filter to remove low-frequency noise
    const lowCutFilter = audioContext.createBiquadFilter();
    lowCutFilter.type = "highpass";
    lowCutFilter.frequency.value = 100; // Cut frequencies below 100Hz

    // Chain the audio processing nodes
    microphone.connect(lowCutFilter);
    lowCutFilter.connect(gainNode);
    gainNode.connect(analyser);

    analyser.smoothingTimeConstant = 0.5;
    analyser.fftSize = 512; // Smaller FFT size for better performance

    // Initialize visualizer
    const statusElement = document.getElementById("status");
    statusElement.id = "status"; // Assign the visualizer ID to the existing element
    statusElement.classList.add("status-indicator"); // Add necessary classes
    statusElement.style.display = "block"; // Ensure it's visible

    const visualizer = new AudioVisualizer(statusElement); // Pass the element directly
    visualizer.connect(analyser);

    // Load silence detector
    await audioContext.audioWorklet.addModule("static/js/silence-detector.js");
    const silenceDetectorNode = new AudioWorkletNode(
      audioContext,
      "silence-detector",
      {
        parameterData: {
          // Parameters for the silence detector worklet
          silenceThreshold: -50, // dB - adjust based on your needs
          minSilenceDuration: 1.5, // seconds
        },
      }
    );

    analyser.connect(silenceDetectorNode);
    silenceDetectorNode.connect(audioContext.destination);

    mediaRecorder = new MediaRecorder(stream, {
      mimeType: "audio/webm;codecs=opus",
      audioBitsPerSecond: 128000,
    });

    let audioChunks = [];
    let silenceStartTime = null;
    let isSilent = false;
    const SILENCE_TIMEOUT = 3000;

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    await new Promise((resolve) => {
      mediaRecorder.onstart = () => {
        visualizer.setStatus("Listening...");
        isListening = true;
        resolve();
      };
      mediaRecorder.start();
    });

    mediaRecorder.onstop = async () => {
      isRecording = false;
      isListening = false;
      visualizer.setStatus("Processing...");
      visualizer.stop();
      isProcessing = true;

      try {
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });

        stream.getTracks().forEach((track) => track.stop());
        audioContext.close();

        await sendAudioToWhisper(audioBlob);
      } catch (error) {
        console.error("Error processing audio:", error);
        visualizer.setStatus("Error processing audio");
      } finally {
        isProcessing = false;
      }
    };

    silenceDetectorNode.port.onmessage = (event) => {
      const { isSilentDetected } = event.data;

      if (isSilentDetected) {
        if (!silenceStartTime) {
          silenceStartTime = Date.now();
        } else if (Date.now() - silenceStartTime > SILENCE_TIMEOUT) {
          if (!isSilent) {
            console.log("Silence detected. Stopping recording...");
            isSilent = true;
            visualizer.setStatus("Processing...");
            mediaRecorder.stop();
          }
        }
      } else {
        silenceStartTime = null;
        isSilent = false;
      }
    };
  } catch (error) {
    console.error("Error starting recording:", error);
    const statusElement = document.getElementById("status");
    statusElement.textContent = "Error accessing microphone";
  }
}

// Add CSS to the document
document.head.insertAdjacentHTML(
  "beforeend",
  `
 <style>    
    .audio-bars {
      display: flex;
      align-items: center;
      justify-content: center;
      height: 60px;
    }
    
    .status-indicator {
        margin-top: 10px !important;
        font-style: italic !important;
        color: white !important;
        text-align: center;
        clear: both;
    }
    .audio-bar {
      will-change: height, background-color;
      animation: pulse 2s infinite alternate;
    }
    
    @keyframes pulse {
      0% { opacity: 0.9; }
      100% { opacity: 1; }
    }
  </style>
`
);

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    isListening = false;
  }
}

// Add CSS to the document

async function sendAudioToWhisper(audioBlob) {
  console.log("Sending audio to Whisper");

  // Check if the audioBlob is empty
  if (audioBlob.size === 0) {
    console.log("No audio recorded. Calling handleNoResponse...");
    handleNoResponse();
    return;
  }

  // Check if the audio contains valid speech
  const audioArrayBuffer = await audioBlob.arrayBuffer();
  const audioContext = new (window.AudioContext || window.webkitAudioContext)();
  const audioBuffer = await audioContext.decodeAudioData(audioArrayBuffer);

  let volume = 0;
  const bufferLength = audioBuffer.length;
  const audioData = audioBuffer.getChannelData(0);

  for (let i = 0; i < bufferLength; i++) {
    volume += audioData[i] * audioData[i];
  }
  volume = Math.sqrt(volume / bufferLength);
  console.log("Audio volume:", volume);

  const SILENCE_THRESHOLD = 0.01;
  if (volume < SILENCE_THRESHOLD) {
    console.log("Audio is silent or too quiet. Calling handleNoResponse...");
    handleNoResponse();
    return;
  }

  // Create FormData and append the audio blob
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.webm");

  try {
    const response = await fetch("/transcribe", {
      method: "POST",
      body: formData,
      headers: { "Accept-Language": "en-US" },
    });

    if (!response.ok) {
      console.log(
        "Invalid or non-English response detected. Calling handleNoResponse..."
      );
      handleNoResponse();
      return;
    }

    const data = await response.json();

    if (!data.text || data.text.trim() === "") {
      console.log("No transcription found.");
      handleNoResponse();
      return;
    }

    console.log("Recognized text:", data.text);

    responseBuffer = data.text;
    addMessage(responseBuffer, true);
    console.log("Response Buffer:", responseBuffer);
    await processUserResponse(responseBuffer.trim());
  } catch (error) {
    console.error("Error in Whisper transcription:", error);
    isError = true; // Set error flag
    status.textContent = "Error transcribing audio";
  } finally {
    isProcessing = false;
  }
}

function handleError(error) {
  console.error("Error:", error);
  status.textContent = "An error occurred";
  isListening = false;

  if (mediaRecorder) {
    mediaRecorder.stream.getTracks().forEach((track) => track.stop());
  }
}

async function processUserResponse(response) {
  console.log(" Processing response !!");
  voiceBtn.disabled = true;
  if (processingResponse) return;
  processingResponse = true;
  retryCount = 0; // Reset retry count on valid response

  if (
    response.toLowerCase().includes("skip") ||
    response.toLowerCase().includes("next question")
  ) {
    currentQuestionIndex++; // Skip the current question
    if (currentQuestionIndex >= questions.length) {
      await endInterview();
    } else {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await askCurrentQuestion(); // Ask the next question
    }
    processingResponse = false; // Ensure processingResponse is reset after skip
    return; // Exit early to prevent further processing for skip/next question
  }

  try {
    console.log(" Sending response to api");
    const evaluation = await callOpenAIAPI(response);
    console.log(" Response recieved");
    if (evaluation.isValid) {
      qaPairs.push(
        `Question: ${questions[currentQuestionIndex]}\nAnswer: ${response}`
      );
      interviewData.responses[questions[currentQuestionIndex]] = response;
      currentQuestionIndex++;

      if (currentQuestionIndex >= questions.length) {
        await endInterview();
      } else {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        await askCurrentQuestion();
      }
    } else {
      await speak(evaluation.feedback);
      if (evaluation.suggestion) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        await speak(evaluation.suggestion);
      }
      startListening();
    }
  } catch (error) {
    console.error("Error:", error);
    isError = true;
    await endInterview("Sorry, there was an error processing your response.");
  } finally {
    processingResponse = false;
    isProcessing = false;
  }
}

async function callOpenAIAPI(userResponse) {
  // Don't process if interview is complete
  if (currentQuestionIndex >= questions.length) {
    return null;
  }

  try {
    const prompt = `You are a very Friendly HR professional. Your goal is to have a natural conversation with the user
      to gather all the information needed for creating a comprehensive job description. ask questions in short,  Use
      open-ended questions and follow-up prompts to encourage detailed responses. After the
      conversation, summarize the gathered information in the dictated outline. This is the only goal
      you need to accomplish in this conversation. Do not allow the conversation steer away from
      extracting information.: Your objective is to extract information about:
      1. The role or position that the user wants to be filled
      2. The user’s ideal person for the role
      3. What are the top three characteristics in the person who the user looking for?
      4. What are the responsibilities of the role?
      5. What experiences are important?
      6. Can the user describe the work environment?
      7. Can the user describe the culture of the company?
      8. What are the perks of the role?
      9. Is there a clear career path for the person in the role?
      10. What is the ideal starting date for the position?
      11. What is the salary range for the role?
      12. Are there any specific skills that the person has to have?
      13. Is the role a hybrid role? If yes, how many days are they expected to be in the office?
      14. What are the major targets or milestones for the role?
      Be responsive to the user's answers, asking for clarification or more details when needed. If the
      user seems unsure about a topic, offer one example or suggestion in very short line to help them think it through.
      Emphasize at the beginning of the conversation that the more detailed their responses are, the
      better their final content plan will be.

      Remember:
      - Adapt your language to the user's level of expertise. Explain concepts if they seem unfamiliar
      with content marketing terms.
      -  ask about information clearly and concisely
      - try to ask question in short one line, ask only questions only which is defined didn't ask questions in detail.
      - If the user provides information that fits multiple categories, make note of it accordingly.
      - It's okay if you don't get perfect information for every category. Work with what the user
      provides.
      - ask only one question in one time.
      - Fix grammatical errors and reformat the user's responses when they provide incomplete answers to questions.
      - Correct any typos or grammatical errors in the user's responses.
      - Reformat unclear answers to ensure clarity.
      - You do not need to ask about exact dates or overly specific timings.
      - If the user provides a brief answer about the Role Information, work environment, company culture, etc do not ask for additional details
      - If a response from the user answers multiple questions from "Information to Gather," you may
      consider each of them answered. You do not need to ask questions that have already been
      answered.


      Language Guidelines:
      [1. Language should be incredibly straightforward and easy to understand.
      2. Write at a 3rd-5th grade reading level.
      3.Maintain a friendly, informal, and conversational tone.
      4.Acknowledge answers naturally but don’t overuse affirmations.
      5.Use varied sentence structures to avoid sounding robotic.]

      Tone Guidelines:
      [
      1.Use a friendly and approachable tone.
      2.Write as if you are speaking to a friend or a family member.
      3.Maintain a friendly, informal, and conversational tone.
      4.Acknowledge the user's feelings and perspectives.
      5.Use varied sentence structures to avoid sounding robotic.]

      Conversation Flow Guidelines:
      [1. Only ask one question at a time.
      2. Accept short or detailed responses without prompting for further clarification unless the answer is unclear.
      2. If the user doesn't know the answer to an individual question, that's ok. Just move on to the
      next bit of information to gather.
      3. If the user's answer doesn't make sense in the context of the question, Use concise language to explain questions or concepts when the user seems uncertain. Avoid lengthy examples.
      of the user's time.
      5. If the user is confused by a question and asks for clarification, clarify in short line.
      6. If the user provides a brief answer about the Role Information,work environment,company culture,etc do not ask for additional details
      7. If a response from the user answers multiple questions from "Information to Gather," you may
      consider each of them answered. You do not need to ask questions that have already been
      answered.
      8. When the user starts speaking, stop typing and only listen.
      9. After you have gathered ALL of the given "Information to gather," end the conversation by
      asking if the user has any other information they forgot to add. If not, thank the user for their
      time and politely sign off.]
      Outline to fill out at the end of the conversation
      Role Information
      [Summarise the ideal person for the role here]
      Company Information
      [Summarize the company information here]
      Expertise:
      [List the main areas of expertise for the role here]
      Roles & Responsibilities
      [List the roles and responsibilities here]
      Starting date
      [State the proposed starting date for the role here]
      Your conversation should feel natural and helpful, not like a rigid questionnaire. Adapt to the
      user’s needs and knowledge level throughout the interaction.

      Please evaluate the user's answer and respond in the following format:
      {
          "isValid": boolean,
          "feedback": "Single concise response with guidance if needed"
      }

    Question: ${questions[currentQuestionIndex]}
    User's Answer: ${userResponse}`;

    const response = await fetch(`https://api.openai.com/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        model: "gpt-4o",
        messages: [
          {
            role: "system",
            content: prompt,
          },
          {
            role: "user",
            content: userResponse,
          },
        ],
        max_tokens: 500,
        temperature: 0.7,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      console.error("API Error Details:", errorData);
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();

    if (!data.choices || !data.choices[0] || !data.choices[0].message) {
      throw new Error("Invalid API response format");
    }

    const botResponse = data.choices[0].message.content;
    let parsedResponse;
    try {
      // Clean the response by removing markdown code blocks and finding the JSON object
      const cleanedResponse = botResponse
        .replace(/```json\n|\n```/g, "")
        .trim();
      parsedResponse = JSON.parse(cleanedResponse);
    } catch (error) {
      console.error("Failed to parse API response:", error);
      console.log("Raw response:", botResponse); // Add this for debugging
      return {
        isValid: false,
        feedback: "I couldn't properly evaluate your response.",
        suggestion: "Could you please provide more details?",
      };
    }

    return parsedResponse;
  } catch (error) {
    console.error("OpenAI API Error:", error);
    return {
      isValid: false,
      feedback: "There was an error processing your response.",
      suggestion: "Could you please try again?",
    };
  } finally {
    isProcessing = false;
  }
}

function saveText() {
  const text = qaPairs.join("\n\n");
  fetch("/save-text", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text: text }),
  })
    .then((response) => response.json())
    .then((data) => {
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

async function endInterview(
  message = "Thank you for providing all the information!"
) {
  if (Object.keys(interviewData.responses).length > 0) {
    saveText();
  }
  await speak(message);

  status.textContent = "Conversation complete";
  voiceBtn.disabled = false;
}

async function startConversation() {
  console.log(" start conversation method called !");
  voiceBtn.disabled = true;
  interviewData.chatHistory = [];
  while (chatOutput.firstChild) {
    chatOutput.removeChild(chatOutput.firstChild);
  }
  // Check if the current question index is valid
  if (currentQuestionIndex < questions.length) {
    // Resume from the last answered question
    console.log(`Resuming from question index: ${currentQuestionIndex}`);
  } else {
    // If all questions have been answered, reset to the first question
    console.log("Starting from the beginning");
    currentQuestionIndex = 0; // Start from the first question
    interviewData.responses = {}; // Reset previous responses
  }

  retryCount = 0; // Reset retry count
  await askCurrentQuestion(); // Ask the current question
}

async function callGeminiAPI(userResponse) {
  // Don't process if interview is complete
  if (currentQuestionIndex >= questions.length) {
    return null;
  }

  try {
    const prompt = {
      contents: [
        {
          parts: [
            {
              text: `You are a very helpful HR professional. Your goal is to have a natural conversation with the user
      to gather all the information needed for creating a comprehensive job description. ask questions in short,  Use
      open-ended questions and follow-up prompts to encourage detailed responses. After the
      conversation, summarize the gathered information in the dictated outline. This is the only goal
      you need to accomplish in this conversation. Do not allow the conversation steer away from
      extracting information.: Your objective is to extract information about:
      1. The role or position that the user wants to be filled
      2. The user’s ideal person for the role
      3. What are the top three characteristics in the person who the user looking for?
      4. What are the responsibilities of the role?
      5. What experiences are important?
      6. Can the user describe the work environment?
      7. Can the user describe the culture of the company?
      8. What are the perks of the role?
      9. Is there a clear career path for the person in the role?
      10. What is the ideal starting date for the position?
      11. What is the salary range for the role?
      12. Are there any specific skills that the person has to have?
      13. Is the role a hybrid role? If yes, how many days are they expected to be in the office?
      14. What are the major targets or milestones for the role?
      Be responsive to the user's answers, asking for clarification or more details when needed. If the
      user seems unsure about a topic, offer one example or suggestion in very short line to help them think it through.
      Emphasize at the beginning of the conversation that the more detailed their responses are, the
      better their final content plan will be.

      Remember:
      - Adapt your language to the user's level of expertise. Explain concepts if they seem unfamiliar
      with content marketing terms.
      -  ask about information clearly and concisely
      - try to ask question in short one line, ask only questions only which is defined didn't ask questions in detail.
      - If the user provides information that fits multiple categories, make note of it accordingly.
      - It's okay if you don't get perfect information for every category. Work with what the user
      provides.
      - ask only one question in one time.
      - Fix grammatical errors and reformat the user's responses when they provide incomplete answers to questions.
      - Correct any typos or grammatical errors in the user's responses.
      - Reformat unclear answers to ensure clarity.
      - You do not need to ask about exact dates or overly specific timings.
      - If the user provides a brief answer about the Role Information, work environment, company culture, etc do not ask for additional details
      - If a response from the user answers multiple questions from "Information to Gather," you may
      consider each of them answered. You do not need to ask questions that have already been
      answered.


      Language Guidelines:
      [1. Language should be incredibly straightforward and easy to understand.
      2. Write at a 3rd-5th grade reading level.
      3. Keep tone informal, unprofessional, colloquial, and light.
      4. Vary your sentence structure.
      5. You may use acknowledgements and affirmations after the user's responses, but vary them
      and don't use them every time. We don't want to sound robotic.
      6. Do not ask the questions from "Information to Gather" verbatim. Instead, edit the questions so
      they follow the language guidelines, but extract the same information.]

      Tone Guidelines:
      [
      1.Use straightforward, easy-to-understand language.
      2.Write at a 3rd-5th grade reading level.
      3.Maintain a friendly, informal, and conversational tone.
      4.Acknowledge answers naturally but don’t overuse affirmations.
      5.Use varied sentence structures to avoid sounding robotic.]

      Conversation Flow Guidelines:
      [1. Only ask one question at a time.
      2. Accept short or detailed responses without prompting for further clarification unless the answer is unclear.
      2. If the user doesn't know the answer to an individual question, that's ok. Just move on to the
      next bit of information to gather.
      3. If the user's answer doesn't make sense in the context of the question, Use concise language to explain questions or concepts when the user seems uncertain. Avoid lengthy examples.
      of the user's time.
      5. If the user is confused by a question and asks for clarification, clarify in short line.
      6. If the user provides a brief answer about the Role Information,work environment,company culture,etc do not ask for additional details
      7. If a response from the user answers multiple questions from "Information to Gather," you may
      consider each of them answered. You do not need to ask questions that have already been
      answered.
      8. When the user starts speaking, stop typing and only listen.
      9. After you have gathered ALL of the given "Information to gather," end the conversation by
      asking if the user has any other information they forgot to add. If not, thank the user for their
      time and politely sign off.]
      Outline to fill out at the end of the conversation
      Role Information
      [Summarise the ideal person for the role here]
      Company Information
      [Summarize the company information here]
      Expertise:
      [List the main areas of expertise for the role here]
      Roles & Responsibilities
      [List the roles and responsibilities here]
      Starting date
      [State the proposed starting date for the role here]
      Your conversation should feel natural and helpful, not like a rigid questionnaire. Adapt to the
      user’s needs and knowledge level throughout the interaction.

      Please evaluate the user's answer and respond in the following format:
      {
          "isValid": boolean,
          "feedback": "Single concise response with guidance if needed"
      }

Question: ${questions[currentQuestionIndex]}
User's Answer: ${userResponse}`,
            },
          ],
        },
      ],
    };

    console.log("Request body:", JSON.stringify(prompt)); // Debug log

    const response = await fetch(
      `${GEMINI_API_ENDPOINT}?key=${GEMINI_API_KEY}`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(prompt),
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      console.error("API Error Details:", errorData);
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    console.log("API Response:", data);

    if (
      !data.candidates ||
      !data.candidates[0] ||
      !data.candidates[0].content
    ) {
      throw new Error("Invalid API response format");
    }

    const botResponse = data.candidates[0].content.parts[0].text;
    let parsedResponse;
    try {
      // Clean the response by removing markdown code blocks and finding the JSON object
      const cleanedResponse = botResponse
        .replace(/```json\n|\n```/g, "")
        .trim();
      parsedResponse = JSON.parse(cleanedResponse);
    } catch (error) {
      console.error("Failed to parse API response:", error);
      console.log("Raw response:", botResponse); // Add this for debugging
      return {
        isValid: false,
        feedback: "I couldn't properly evaluate your response.",
        suggestion: "Could you please provide more details?",
      };
    }

    return parsedResponse;
  } catch (error) {
    console.error("Gemini API Error:", error);
    return {
      isValid: false,
      feedback: "There was an error processing your response.",
      suggestion: "Could you please try again?",
    };
  }
}

function saveResults() {
  const jsonData = JSON.stringify(interviewData, null, 2);

  fetch("/save-interview", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: jsonData,
  })
    .then((response) => {
      if (!response.ok) throw new Error("Failed to save interview data");
      console.log("Interview data saved successfully");
    })
    .catch((error) => {
      console.error("Error saving interview data:", error);
    });
}

function openCenteredAlert() {
  Swal.fire({
    title: "Close AI Assistant?",
    text: "Are you sure you want to close the AI Assistant? Any unsaved progress will be lost.",
    icon: "warning",
    showCancelButton: true, // Enables the Cancel button
    confirmButtonText: "Yes, Close",
    cancelButtonText: "Cancel",
    reverseButtons: true, // Optional: swaps the order of the buttons
    preConfirm: () => {
      // Action when "OK" is pressed
      closeAIChat();
    },
  });
}

function generateSummary() {
  let summaryText = `Interview Summary - ${new Date().toLocaleString()}\n\n`;
  summaryText += "Chat History:\n";
  interviewData.chatHistory.forEach((entry, index) => {
    summaryText += `${index + 1}. Question: ${entry.question}\n   Answer: ${
      entry.answer
    }\n\n`;
  });
  return summaryText;
}

function saveSummary() {
  const summary = generateSummary();

  // Create a blob with the summary text
  const blob = new Blob([summary], { type: "text/plain" });

  // Create a link element
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "Interview_Summary.txt";

  // Trigger the download
  link.click();

  // Clean up the object URL
  URL.revokeObjectURL(link.href);
}

function closeAIChat() {
  document.getElementById("aiChatPopup").style.display = "none";
  document.getElementById("overlay").style.display = "none";
  stopAI();
  console.log(" 581 stopplistening");
  currentQuestionIndex = 0;
  location.reload();
  retryCount = 0;
  responseBuffer = "";
  interviewData.responses = {};
}

function stopAI() {
  if (synth) {
    synth.pause();
    synth.cancel(); // Cancel ongoing speech synthesis
  }
  if (recognition) {
    try {
      recognition.stop(); // Stop voice recognition
      return;
    } catch (e) {
      console.error("Error stopping voice recognition:", e);
    }
  }
}

function toggleDropdown(event) {
  event.stopPropagation(); // Prevent closing immediately after opening
  const dropdownMenu = document.getElementById("dropdown-menu");

  // Toggle visibility
  dropdownMenu.style.display =
    dropdownMenu.style.display === "block" ? "none" : "block";

  // Close dropdown when clicking outside
  document.addEventListener("click", function closeDropdown(e) {
    if (!event.target.closest(".dropdown")) {
      dropdownMenu.style.display = "none";
      document.removeEventListener("click", closeDropdown);
    }
  });
}

function handleLogout(event) {
  event.preventDefault(); // Prevent direct navigation
  Swal.fire({
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
