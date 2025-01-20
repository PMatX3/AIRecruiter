        const GEMINI_API_KEY = 'AIzaSyDJnRYm3-t06ks4zrBFyEglV6qJyFvn8Qo';
        const GEMINI_API_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent';

        
        const chatOutput = document.getElementById('chat-output');
        const voiceBtn = document.getElementById('voice-btn');
        const stopBtn = document.getElementById('stop-btn');
        const status = document.getElementById('status');


        let recognition = null;
        let currentQuestionIndex = 0;
        let retryCount = 0;
        let responseBuffer = '';
        let silenceTimer = null;
        let processingResponse = false;
        
        const MAX_RETRIES = 2;
        const SILENCE_TIMEOUT = 6000;
        
        const questions = [
            "What is the job title or position you want to be filled?",
            "What does your ideal candidate for this role look like?",
            "What are the three most important characteristics or qualities you're looking for in the person filling this role?",
            "What are the main responsibilities for this position?",
            "What specific experiences are required or highly valued for the role?",
            "Can you briefly describe the work environment?",
            "Can you describe the company culture in a few sentences?",
            "Is there a clear career progression or growth path for the candidates in this role?",
            "What is the ideal starting date for this position?",
            "What is the salary range for the role?",
            "Are there any specific skills or qualifications the candidate must have?",
            "Is the role hybrid? If so, how many days per week will the person be required to be in the office?",
            "What are the key performance targets or milestones for the person in this role?"
        ];

        let interviewData = {
            timestamp: new Date().toISOString(),
            responses: {}
        };

        const synth = window.speechSynthesis;

        function speak(text) {
            return new Promise(resolve => {
                const utterance = new SpeechSynthesisUtterance(text);
                utterance.onend = resolve;
                utterance.onerror = resolve;
                synth.speak(utterance);
                addMessage(text, false);
            });
        }

        const preloadImage = new Image();
            preloadImage.src = "../static/images/ai_img6.jpeg";
            preloadImage.onload = function () {
                document.querySelector('.chat-container').style.backgroundImage = `url(${preloadImage.src})`;
        };

        function openAIChat() {
            document.getElementById('aiChatPopup').style.display = 'block';
            document.getElementById('overlay').style.display = 'block';
            // Reset chat
            voiceChatQuestionIndex = 0;
            voiceChatHistory = [];
            qaPairs = [];
            document.getElementById('chat-output').innerHTML = '';
            document.getElementById('voice-btn').disabled = false;
        }

        function addMessage(text, isUser) {
            const div = document.createElement('div');
            div.className = `message chat-bubble ${isUser ? 'user-message' : 'bot-message'}`;
            div.textContent = text;
            chatOutput.appendChild(div);
            chatOutput.scrollTop = chatOutput.scrollHeight;
            setTimeout(() => div.classList.add('visible'), 100);
        }

        async function handleNoResponse() {
            if (retryCount < MAX_RETRIES) {
                retryCount++;
                await speak("I didn't hear your response. Let me repeat the question.");
                await askCurrentQuestion();
            } else {
                await endInterview("No response received after multiple attempts. Ending conversation.");
            }
        }

        async function askCurrentQuestion() {
            if (currentQuestionIndex < questions.length) {
                status.textContent = 'Speaking question...';
                await speak(questions[currentQuestionIndex]);
                startListening();
            }
        }

        function startListening() {console.err
            if (recognition) recognition.stop();
            
            recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';
            responseBuffer = '';
            status.textContent = 'Listening...';
            stopBtn.style.display = 'inline-block';
            stopBtn.disabled = false;

            // Set timeout for no response
            silenceTimer = setTimeout(() => handleNoResponse(), 15000);

            recognition.onresult = (event) => {
                clearTimeout(silenceTimer);
                let interim = '';
                let final = '';

                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        final += transcript + ' ';
                        responseBuffer += transcript + ' ';
                    } else {
                        interim += transcript;
                    }
                }

                status.textContent = interim ? 'Listening: ' + interim : 'Listening...';
                
                // Reset silence timer when user speaks
                silenceTimer = setTimeout(() => {
                    if (responseBuffer.trim()) {
                        stopListening();
                        addMessage(responseBuffer.trim(), true);
                        processUserResponse(responseBuffer.trim());
                    } else {
                        handleNoResponse();
                    }
                }, SILENCE_TIMEOUT);
            };

            recognition.onend = () => {
                
                if (!recognition) {
                    return;
                }
            };

            recognition.onerror = (event) => {
                console.error('Recognition error:', event.error);
                clearTimeout(silenceTimer);
                if (event.error === 'no-speech') {
                    handleNoResponse();
                } else {
                    endInterview("There was an error with speech recognition.");
                }
            };

            try {
                recognition.start();
            } catch (error) {
                console.error('Error starting recognition:', error);
                endInterview("Failed to start speech recognition.");
            }
        }

        function stopListening() {
            
            if (synth && synth.speaking) {
                
                synth.cancel(); // Stops all utterances
            }
            if (recognition) {
                recognition.stop();
                recognition.onend = null;
                recognition.onerror = null;
                recognition.onresult= null;
            }
            clearTimeout(silenceTimer);
            stopBtn.disabled = true;
            status.textContent = '';
            document.getElementById('voice-btn').disabled = false;
        }

        async function processUserResponse(response) {
            if (processingResponse) return;
            processingResponse = true;
            retryCount = 0; // Reset retry count on valid response

            try {
                const evaluation = await callGeminiAPI(response);
                
                if (evaluation.isValid) {
                    interviewData.responses[questions[currentQuestionIndex]] = response;
                    currentQuestionIndex++;

                    if (currentQuestionIndex >= questions.length) {
                        await endInterview();
                    } else {
                        await new Promise(resolve => setTimeout(resolve, 1000));
                        await askCurrentQuestion();
                    }
                } else {
                    await speak(evaluation.feedback);
                    if (evaluation.suggestion) {
                        await new Promise(resolve => setTimeout(resolve, 500));
                        await speak(evaluation.suggestion);
                    }
                    startListening();
                }
            } catch (error) {
                console.error('Error:', error);
                await endInterview("Sorry, there was an error processing your response.");
            } finally {
                processingResponse = false;
            }
        }

        async function endInterview(message = "Thank you for providing all the information!") {
            stopListening();
            if (Object.keys(interviewData.responses).length > 0) {
                saveResults();
            }
            await speak(message);
            voiceBtn.disabled = false;
            stopBtn.style.display = 'none';
            status.textContent = 'Conversation complete';
        }

        async function startConversation() {
            voiceBtn.disabled = true;
            currentQuestionIndex = 0;
            retryCount = 0;
            interviewData.responses = {};
            await askCurrentQuestion();
        }

        async function callGeminiAPI(userResponse) {
            // Don't process if interview is complete
            if (currentQuestionIndex >= questions.length) {
                return null;
            }

            try {
                const prompt = {
                    contents: [{
                        parts: [{
                            text: `You are a very helpful HR professional. Your goal is to have a natural conversation with the user
      to gather all the information needed for creating a comprehensive job description. ask questions in short,  Use
      open-ended questions and follow-up prompts to encourage detailed responses. After the
      conversation, summarize the gathered information in the dictated outline. This is the only goal
      you need to accomplish in this conversation. Do not allow the conversation steer away from
      extracting information.: Your objective is to extract information about:
      1. The role or position that the user wants to be filled
      2. The user’s ideal person for the role

      Be responsive to the user's answers, asking for clarification or more details when needed. If the
      user seems unsure about a topic, offer examples or suggestions  in very short line to help them think it through.
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
User's Answer: ${userResponse}`
                        }]
                    }]
                };

                console.log('Request body:', JSON.stringify(prompt)); // Debug log

                const response = await fetch(`${GEMINI_API_ENDPOINT}?key=${GEMINI_API_KEY}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(prompt)
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    console.error('API Error Details:', errorData);
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                console.log('API Response:', data);

                if (!data.candidates || !data.candidates[0] || !data.candidates[0].content) {
                    throw new Error('Invalid API response format');
                }

                const botResponse = data.candidates[0].content.parts[0].text;
                let parsedResponse;
                try {
                    // Clean the response by removing markdown code blocks and finding the JSON object
                    const cleanedResponse = botResponse.replace(/```json\n|\n```/g, '').trim();
                    parsedResponse = JSON.parse(cleanedResponse);
                } catch (error) {
                    console.error('Failed to parse API response:', error);
                    console.log('Raw response:', botResponse); // Add this for debugging
                    return {
                        isValid: false,
                        feedback: "I couldn't properly evaluate your response.",
                        suggestion: "Could you please provide more details?"
                    };
                }

                return parsedResponse;
            } catch (error) {
                console.error('Gemini API Error:', error);
                return {
                    isValid: false,
                    feedback: "There was an error processing your response.",
                    suggestion: "Could you please try again?"
                };
            }
        }

        function saveResults() {
            const jsonData = JSON.stringify(interviewData, null, 2);
            
            fetch('/save-interview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: jsonData
            })
            .then(response => {
                if (!response.ok) throw new Error('Failed to save interview data');
                console.log('Interview data saved successfully');
            })
            .catch(error => {
                console.error('Error saving interview data:', error);
            });
        }


        function openCenteredAlert() {
            Swal.fire({
                title: 'Close AI Assistant?',
                text: 'Are you sure you want to close the AI Assistant? Any unsaved progress will be lost.',
                icon: 'warning',
                showCancelButton: true, // Enables the Cancel button
                confirmButtonText: 'Yes, Close',
                cancelButtonText: 'Cancel',
                reverseButtons: true, // Optional: swaps the order of the buttons
                preConfirm: () => {
                    // Action when "OK" is pressed
                    closeAIChat();
                }
            });
        }

        function closeAIChat() {
            document.getElementById('aiChatPopup').style.display = 'none';
            document.getElementById('overlay').style.display = 'none';
            if (synth && synth.speaking) {
                synth.cancel(); // Stops all utterances
            }
            stopListening();
            currentQuestionIndex = 0;
            retryCount = 0;
            responseBuffer = ''; 
            interviewData.responses = {};
        }

        function resetVoiceChat() {

        }

        
        