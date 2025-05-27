// navbar-loader.js

// Function to load the navbar component
async function loadNavbar() {
    try {
      // Fetch the navbar HTML
      const response = await fetch('/components/navbar.html');
      if (!response.ok) {
        throw new Error(`Failed to fetch navbar: ${response.status}`);
      }
      
      const navbarHtml = await response.text();
      
      // Create a container to hold the navbar
      const navbarContainer = document.createElement('div');
      navbarContainer.innerHTML = navbarHtml;
      
      // Insert the navbar at the beginning of the body
      document.body.insertAdjacentElement('afterbegin', navbarContainer.firstElementChild);
      
      // Load the navbar script
      const script = document.createElement('script');
      script.src = '/components/navbar.js';
      script.type = 'module';
      document.head.appendChild(script);
      
      // Add padding to body to account for fixed navbar height
      const navbar = document.getElementById('main-navbar');
      const navbarHeight = navbar.offsetHeight;
      document.body.style.paddingTop = `${navbarHeight}px`;
      
      console.log('Navbar loaded successfully');
    } catch (error) {
      console.error('Error loading navbar:', error);
    }
  }
  
  // Load the navbar when the DOM is fully loaded
  document.addEventListener('DOMContentLoaded', loadNavbar);
  
  // Export the loadNavbar function
  export { loadNavbar };