// login.js: Handles user login using localStorage

document.getElementById('login-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const messageDiv = document.getElementById('login-message');

  const users = JSON.parse(localStorage.getItem('civiclens_users') || '{}');
  if (!users[username] || users[username].password !== password) {
    messageDiv.textContent = 'Invalid username or password.';
    messageDiv.style.color = 'red';
    return;
  }

  // Save logged in user
  localStorage.setItem('civiclens_loggedin', username);
  messageDiv.textContent = 'Login successful! Redirecting...';
  messageDiv.style.color = 'green';
  setTimeout(() => {
    window.location.href = 'portal.html';
  }, 1000);
});
