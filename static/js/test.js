document.addEventListener('DOMContentLoaded', (event) => {
    // const socket = io('http://192.168.0.14:5000/')
    const socket = io('http://192.168.0.14:5000/', { autoConnect: false })

    // Chat DOM elements
    const chatInput = $('#chatInput')
    const chatSendButton = $('#chatSendButton')
    const chatContent = $('.chatContent');
    const SessionForm = $('#SessionForm');

    // Coordinates DOM elements
    const cooordinatesInput = $('#coordinates_user_id')
    const cooordinatesSendButton = $('#cooordinatesSendButton')

    //Login button
    const loginButton = $('#loginButton')


    // Link button to send post request to login user. This approach choosen to manage WebSocket connection manually
    $('#loginButton').on('click', function (event) {
        var username = $('input[name="name"]').val();
        var password = $('input[name="password"]').val();

        var loginUrl = $('#loginButton').data('login-url');
        var testPageUrl = $('#loginButton').data('test-page-url');


        $.post(loginUrl, { name: username, password: password }, function (response) {
            if (response.status === 'success') {
                socket.connect();

                setTimeout(function () {
                    window.location.href = testPageUrl;
                }, 500);
            } else {
                console.log('Login failed:', response.message);
                alert('Login failed: ' + response.message);
            }
        }, 'json');
    });

    // Chat button emit to server
    chatSendButton.click(function () {
        const message = chatInput.val().trim();
        if (message !== "") {
            // Emit message update
            socket.emit('messageUpdate', message);

            // Clear input
            chatInput.val('');

            // Add sent message to chat box
            const $messageElement = $('<div>').addClass('message sent');
            const $messageText = $('<div>').addClass('messageText').text(message);

            $messageElement.append($messageText);
            chatContent.append($messageElement);
        }
    });


    // Coordinates button emit to server
    cooordinatesSendButton.on('click', function () {
        const latitude = 52.40833333333333;
        const longitude = 16.93333333333333;

        const randomLatOffset = (Math.random() - 0.5) * 0.02;
        const randomLonOffset = (Math.random() - 0.5) * 0.02;
        socket.emit('coordinatesUpdate', { user_id: cooordinatesInput.val(), latitude: latitude + randomLatOffset, longitude: longitude + randomLonOffset });
    });

    $('form').on('submit', function (event) {
        //After getting response do
        socket.connect()
    });

    // Recive updated active_users list from server (with coordinates). For testing purposes to dubug sending coordinates
    socket.on('updatedUsers', (data) => {
        const active_users = $('#active_users');
        active_users.empty();
        data.forEach(user => {
            const userStr = `<p>User ID: ${user.user_id}, Longitude: ${user.longitude}, Latitude: ${user.latitude}</p>`;
            active_users.append(userStr);
        });
    });

    // Create new session in DB
    SessionForm.on('submit', function (event) {
        event.preventDefault();
        socket.emit('sessionUpdate');
    });


    // Show response from server
    socket.on('Alert', (data) => {
        alert(data.message);
    });

    socket.on('sessionCreated', (data) => {
        alert(`
            Session created successfully! Session data:
        Session ID: ${data.id}
        Host Name: ${data.host_name}
        Progress: ${data.progress}
    `);
        console.log("Session Data: ", data);
    });


    // Only for show
    socket.on('connect', function () {
        console.log('Connected to WebSocket');
    });
    socket.on('disconnect', function () {
        console.log('Connected to WebSocket');
    });
    socket.on('response', function (data) {
        console.log('Received response: ' + data);
    });

    socket.send('Hello from client!');


    socket.on('LOGGED', function () {
        console.log('User logged in:');
    });


    socket.on('tasks_update', (data) => {
        if (data.error) {
            console.error('Error:', data.error);
        } else {
            const tasksList = document.getElementById('tasksList');
            tasksList.innerHTML = '';
            data.tasks.forEach(task => {
                const listItem = document.createElement('li');
                listItem.textContent = `ID: ${task.id}, Name: ${task.name}, Status: ${task.status}`;
                tasksList.appendChild(listItem);
            });
        }
    });
});