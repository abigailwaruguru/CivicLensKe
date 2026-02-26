// signup.js: Handles user registration using localStorage

document.getElementById('signup-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const username = document.getElementById('signup-username').value.trim();
  const password = document.getElementById('signup-password').value;
  const messageDiv = document.getElementById('signup-message');

  if (!username || !password) {
    messageDiv.textContent = 'Please fill in all fields.';
    messageDiv.style.color = 'red';
    return;
  }

  // Check if user already exists
  const users = JSON.parse(localStorage.getItem('civiclens_users') || '{}');
  if (users[username]) {
    messageDiv.textContent = 'Username already exists.';
    messageDiv.style.color = 'red';
    return;
  }

  // Save user
  users[username] = { password };
  localStorage.setItem('civiclens_users', JSON.stringify(users));
  messageDiv.textContent = 'Sign up successful! You can now log in.';
  messageDiv.style.color = 'green';
  document.getElementById('signup-form').reset();
});
