// Initialize Lucide icons
lucide.createIcons();

// Features Data
const features = [
  {
    title: "AI-Powered Matching",
    description:
      "Our advanced AI algorithm matches candidates to jobs with unparalleled accuracy.",
    icon: "cpu",
    iconClassName: "bg-recruiter-500",
  },
  {
    title: "Time-Saving",
    description:
      "Reduce your hiring time by up to 80% with automated candidate screening.",
    icon: "clock",
    iconClassName: "bg-recruiter-600",
  },
  {
    title: "Multi-Platform Posting",
    description:
      "Post jobs to multiple platforms with a single click, reaching more candidates.",
    icon: "briefcase",
    iconClassName: "bg-recruiter-700",
  },
  {
    title: "Smart Candidate Selection",
    description:
      "Our semantic search technology finds the best candidates for your positions.",
    icon: "user-check",
    iconClassName: "bg-recruiter-800",
  },
  {
    title: "Comprehensive Analytics",
    description:
      "Get detailed insights into your recruitment process with real-time analytics.",
    icon: "bar-chart",
    iconClassName: "bg-recruiter-500",
  },
  {
    title: "Secure Data Handling",
    description:
      "Your data is protected with enterprise-grade security measures.",
    icon: "shield",
    iconClassName: "bg-recruiter-600",
  },
];

// Testimonials Data
const testimonials = [
  {
    name: "Sarah Johnson",
    role: "HR Manager, TechGlobal",
    content:
      "YourBestRecruiterAI has reduced our time-to-hire by 60%. The quality of candidates has improved significantly.",
  },
  {
    name: "Mark Williams",
    role: "Talent Acquisition, Innovate Inc.",
    content:
      "The AI-powered matching is incredible. We're finding candidates that perfectly fit our company culture and technical requirements.",
  },
  {
    name: "Jennifer Lee",
    role: "Recruiting Lead, StartUp Vision",
    content:
      "As a small startup, our recruiting resources are limited. This platform has been a game-changer for our hiring process.",
  },
];

// Pricing Plans Data
const pricingPlans = [
  {
    name: "Starter",
    price: "$99",
    features: [
      "5 active job postings",
      "50 candidate screenings/month",
      "Basic analytics",
      "Email support",
    ],
    cta: "Get Started",
    popular: false,
  },
  {
    name: "Professional",
    price: "$249",
    features: [
      "20 active job postings",
      "500 candidate screenings/month",
      "Advanced analytics",
      "Priority email & chat support",
      "Job board integrations",
    ],
    cta: "Try Now",
    popular: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    features: [
      "Unlimited job postings",
      "Unlimited screenings",
      "Custom integrations",
      "Dedicated account manager",
      "API access",
      "Custom reporting",
    ],
    cta: "Contact Sales",
    popular: false,
  },
];

const processSteps = [
  {
    id: 1,
    title: "Upload Job Information",
    description:
      "Upload job description, salary, start date, closing date, and contact details through text or voice.",
    icon: "clipboard-check",
  },
  {
    id: 2,
    title: "Process Information",
    description:
      "Our AI processes the job details to create an optimized job description.",
    icon: "cpu",
  },
  {
    id: 3,
    title: "Job Posting",
    description:
      "Connect to LinkedIn and other job boards to post the job description.",
    icon: "share-2",
  },
  {
    id: 4,
    title: "Collect Applications",
    description:
      "Gather applications and create PDFs for every application, including emails and CVs.",
    icon: "inbox",
  },
  {
    id: 5,
    title: "Create Knowledge Base",
    description:
      "Store applications and job description in a searchable knowledge base.",
    icon: "database",
  },
  {
    id: 6,
    title: "Candidate Selection",
    description:
      "Perform semantic search to find the top 30 candidates and generate ranked results.",
    icon: "user-check",
  },
  {
    id: 7,
    title: "Email Ranked Results",
    description:
      "Send ranked results to the client's email with top candidate names.",
    icon: "mail",
  },
  {
    id: 8,
    title: "Client Selection",
    description:
      "Client selects candidates for interviews from the email list.",
    icon: "check-circle",
  },
  {
    id: 9,
    title: "Interview Scheduling",
    description: "Schedule interviews in a shared calendar for all parties.",
    icon: "calendar",
  },
  {
    id: 10,
    title: "Candidate Notifications",
    description:
      "Send email to interviewer and candidates with interview details.",
    icon: "file-text",
  },
];

function createProcessStepElement(step) {
  const stepElement = document.createElement("div");
  stepElement.className =
    "card-glass card-hover p-6 opacity-0 flex flex-col h-full";
  stepElement.style.transitionDelay = `${(step.id - 1) * 100}ms`;

  stepElement.innerHTML = `
        <div class="bg-recruiter-50 p-3 rounded-full w-14 h-14 flex items-center justify-center mb-4">
            <i data-lucide="${step.icon}" class="w-7 h-7 text-recruiter-700"></i>
        </div>
        <div class="flex items-center gap-3 mb-3">
            <div class="bg-recruiter-100 text-recruiter-800 font-medium text-sm px-3 py-1 rounded-full">
                Step ${step.id}
            </div>
            <div class="h-px bg-gray-200 flex-grow"></div>
        </div>
        <h3 class="text-xl font-semibold mb-3 text-gray-900">${step.title}</h3>
        <p class="text-gray-600 flex-grow">${step.description}</p>
    `;

  return stepElement;
}

function initializeProcessFlow() {
  const processFlowContainer = document.getElementById("process-flow");
  if (!processFlowContainer) return;

  // Create and append process steps
  processSteps.forEach((step) => {
    const stepElement = createProcessStepElement(step);
    processFlowContainer.appendChild(stepElement);
  });

  // Initialize Lucide icons
  lucide.createIcons();

  // Set up intersection observer for animations
  const observerOptions = {
    root: null,
    rootMargin: "0px",
    threshold: 0.1,
  };

  const handleIntersect = (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("animate-fade-in-up");
        entry.target.classList.add("opacity-100");
      }
    });
  };

  const observer = new IntersectionObserver(handleIntersect, observerOptions);
  const stepElements = processFlowContainer.querySelectorAll(".card-glass");
  stepElements.forEach((step) => observer.observe(step));
}

// Initialize Features
function initializeFeatures() {
  const featuresGrid = document.getElementById("features-grid");
  features.forEach((feature, index) => {
    const featureCard = document.createElement("div");
    featureCard.className = `card-glass card-hover p-6 flex flex-col h-full`;
    featureCard.style.transitionDelay = `${index * 100}ms`;

    featureCard.innerHTML = `
            <div class="flex-col text-xl items-center gap-4 ">
                <div class="w-12 h-12 rounded-full ${feature.iconClassName} flex items-center bg-recruiter-600 justify-center mb-4">
                    <i data-lucide="${feature.icon}" class="w-6 h-6 text-white "></i>
                </div>
                <h3 class="text-xl font-semibold text-gray-900">${feature.title}</h3>
            </div>
            <p class="text-gray-600">${feature.description}</p>
        `;

    featuresGrid.appendChild(featureCard);
  });
  lucide.createIcons();
}

function initializeHeader() {
  const navbar = document.getElementById("navbar");
  const mobileMenuButton = document.getElementById("mobile-menu-button");
  const mobileMenu = document.getElementById("mobileMenu");
  const menuIcon = document.getElementById("menuIcon");
  const closeIcon = document.getElementById("closeIcon");

  if (!navbar || !mobileMenuButton || !mobileMenu || !menuIcon || !closeIcon)
    return;

  // Handle scroll behavior
  let lastScrollTop = 0;
  window.addEventListener("scroll", () => {
    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;

    if (scrollTop > 60) {
      navbar.classList.remove("bg-transparent");
      navbar.classList.add("bg-white/80", "backdrop-blur-md", "shadow-sm");
    } else {
      navbar.classList.remove("bg-white/80", "backdrop-blur-md", "shadow-sm");
      navbar.classList.add("bg-transparent");
    }

    lastScrollTop = scrollTop;
  });

  // Handle mobile menu toggle
  mobileMenuButton.addEventListener("click", () => {
    const isOpen = mobileMenu.classList.contains("hidden");

    if (isOpen) {
      mobileMenu.classList.remove("hidden");
      menuIcon.classList.add("hidden");
      closeIcon.classList.remove("hidden");
      document.body.style.overflow = "hidden";
    } else {
      mobileMenu.classList.add("hidden");
      menuIcon.classList.remove("hidden");
      closeIcon.classList.add("hidden");
      document.body.style.overflow = "";
    }
  });

  // Close mobile menu when clicking on a link
  const mobileLinks = mobileMenu.querySelectorAll("a");
  mobileLinks.forEach((link) => {
    link.addEventListener("click", () => {
      mobileMenu.classList.add("hidden");
      menuIcon.classList.remove("hidden");
      closeIcon.classList.add("hidden");
      document.body.style.overflow = "";
    });
  });

  // Close mobile menu when clicking outside
  document.addEventListener("click", (e) => {
    if (
      !mobileMenu.contains(e.target) &&
      !mobileMenuButton.contains(e.target)
    ) {
      mobileMenu.classList.add("hidden");
      menuIcon.classList.remove("hidden");
      closeIcon.classList.add("hidden");
      document.body.style.overflow = "";
    }
  });
}

// Initialize Testimonials
function initializeTestimonials() {
  const testimonialsGrid = document.getElementById("testimonials-grid");
  testimonials.forEach((testimonial, index) => {
    const testimonialCard = document.createElement("div");
    testimonialCard.className = `testimonial-card card-glass p-6 reveal-element opacity-0`;
    testimonialCard.style.transitionDelay = `${index * 100}ms`;

    testimonialCard.innerHTML = `
            <div class="flex items-center gap-4 mb-4">
                <div class="w-12 h-12 rounded-full bg-recruiter-100 flex items-center justify-center text-recruiter-700 font-bold">
                    ${testimonial.name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")}
                </div>
                <div>
                    <h4 class="font-semibold text-gray-900">${
                      testimonial.name
                    }</h4>
                    <p class="text-sm text-gray-600">${testimonial.role}</p>
                </div>
            </div>
            <p class="text-gray-700">"${testimonial.content}"</p>
            <div class="mt-4 flex">
                ${[...Array(5)]
                  .map(
                    () => `
                    <svg class="w-5 h-5 text-yellow-400 fill-current" viewBox="0 0 24 24">
                        <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
                    </svg>
                `
                  )
                  .join("")}
            </div>
        `;

    testimonialsGrid.appendChild(testimonialCard);
  });
}

// Initialize Pricing Plans
function initializePricing() {
  const pricingGrid = document.getElementById("pricing-grid");
  pricingPlans.forEach((plan, index) => {
    const pricingCard = document.createElement("div");
    pricingCard.className = `pricing-card card-glass p-6 flex flex-col reveal-element opacity-0 ${
      plan.popular
        ? "border-recruiter-500 transform scale-105 z-10"
        : "border-gray-200"
    }`;
    pricingCard.style.transitionDelay = `${index * 100}ms`;

    pricingCard.innerHTML = `
            ${
              plan.popular
                ? `
                <div class="bg-recruiter-500 text-white text-xs font-bold uppercase tracking-wider py-1 px-3 rounded-full self-start mb-4">
                    Most Popular
                </div>
            `
                : ""
            }
            <h3 class="text-2xl font-bold text-gray-900 mb-2">${plan.name}</h3>
            <div class="mb-6">
                <span class="text-4xl font-bold text-gray-900">${
                  plan.price
                }</span>
                ${
                  plan.price !== "Custom"
                    ? '<span class="text-gray-600">/month</span>'
                    : ""
                }
            </div>
            <ul class="space-y-3 mb-8 flex-grow">
                ${plan.features
                  .map(
                    (feature) => `
                    <li class="flex items-center gap-2">
                        <svg class="w-5 h-5 text-recruiter-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                        </svg>
                        <span class="text-gray-700">${feature}</span>
                    </li>
                `
                  )
                  .join("")}
            </ul>
            <button class="w-full py-3 px-6 rounded-lg font-medium transition-colors duration-300 ${
              plan.popular
                ? "bg-recruiter-500 hover:bg-recruiter-600 text-white"
                : "bg-white hover:bg-gray-100 text-gray-900 border border-gray-200"
            }">
                ${plan.cta}
            </button>
        `;

    pricingGrid.appendChild(pricingCard);
  });
}

// Form Handling
function handleFormSubmit(formId) {
  const form = document.getElementById(formId);
  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    // Show loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.innerHTML = '<div class="loading-spinner"></div>';
    submitButton.disabled = true;

    // Simulate form submission
    setTimeout(() => {
      // Show success message
      showToast("Form submitted successfully!");
      form.reset();
      submitButton.textContent = originalText;
      submitButton.disabled = false;
    }, 1500);
  });
}

// Toast Notification
function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 3000);
}

// Scroll Reveal Animation
function initializeScrollReveal() {
  const observerOptions = {
    root: null,
    rootMargin: "0px",
    threshold: 0.1,
  };

  const handleIntersect = (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("animate-fade-in-up");
        entry.target.classList.remove("opacity-0");
      }
    });
  };

  const observer = new IntersectionObserver(handleIntersect, observerOptions);

  document.querySelectorAll(".reveal-element").forEach((el) => {
    observer.observe(el);
  });
}

// Demo/CTA Section Animation
function initializeDemoSection() {
  const demoSection = document.getElementById("demo");
  if (!demoSection) return;

  const observerOptions = {
    root: null,
    rootMargin: "0px",
    threshold: 0.1,
  };

  const handleIntersect = (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const revealElements = entry.target.querySelectorAll(".reveal-element");
        revealElements.forEach((el, index) => {
          setTimeout(() => {
            el.classList.add("visible");
          }, index * 200);
        });
      }
    });
  };

  const observer = new IntersectionObserver(handleIntersect, observerOptions);
  observer.observe(demoSection);
}

// Initialize everything when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  initializeFeatures();
  initializeTestimonials();
  initializeProcessFlow();
  initializePricing();
  initializeHeader();
  initializeScrollReveal();
  initializeDemoSection();
  handleFormSubmit("demo-form");
  handleFormSubmit("contact-form");
});
