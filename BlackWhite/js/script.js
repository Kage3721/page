document.getElementById('login-form').addEventListener('submit', function (event) {
    event.preventDefault();
    const message = document.getElementById('login-message');
    message.textContent = 'This practice page has no account server. No login details are sent or saved.';
    message.hidden = false;
});
