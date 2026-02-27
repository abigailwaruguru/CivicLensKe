//Handles user registration using localStorage

document.getElementById('signup-form').addEventListener('submit', function(e) {
  e.preventDefault();
  const username = document.getElementById('signup-username').value.trim();
  const email = document.getElementById('signup-email').value.trim();
  const password = document.getElementById('signup-password').value;
  const password2 = document.getElementById('signup-password2').value;
  const messageDiv = document.getElementById('signup-message');

  if (!username || !email || !password || !password2) {
    messageDiv.textContent = 'Please fill in all fields.';
    messageDiv.style.color = 'red';
    return;
  }
  //Basic email format check
  if (!/^\S+@\S+\.\S+$/.test(email)) {
    messageDiv.textContent = 'Please enter a valid email address.';
    messageDiv.style.color = 'red';
    return;
  }
  //Password strength check
  const passwordRequirements = [
    { regex: /.{8,}/, message: 'at least 8 characters' },
    { regex: /[A-Z]/, message: 'an uppercase letter' },
    { regex: /[a-z]/, message: 'a lowercase letter' },
    { regex: /[0-9]/, message: 'a number' },
    { regex: /[^A-Za-z0-9]/, message: 'a special character' }
  ];
  const failed = passwordRequirements.filter(req => !req.regex.test(password));
  if (failed.length > 0) {
    messageDiv.textContent = 'Password must contain ' + failed.map(f => f.message).join(', ') + '.';
    messageDiv.style.color = 'red';
    return;
  }
  if (password !== password2) {
    messageDiv.textContent = 'Passwords do not match.';
    messageDiv.style.color = 'red';
    return;
  }

  //Check if user already exists
  const users = JSON.parse(localStorage.getItem('civiclens_users') || '{}');
  if (users[username]) {
    messageDiv.textContent = 'Username already exists.';
    messageDiv.style.color = 'red';
    return;
  }

  //Save user
  users[username] = { email, password };
  localStorage.setItem('civiclens_users', JSON.stringify(users));
  messageDiv.textContent = 'Sign up successful! You can now log in.';
  messageDiv.style.color = 'green';
  document.getElementById('signup-form').reset();
});
