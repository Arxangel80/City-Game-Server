$(document).ready(function () {
    const socket = io('http://192.168.0.14:5000'); // WebSocket initialization

    // Cache DOM elements
    const $infoArrow = $('#arrow');
    const $content = $('#content');
    const tasksInfoContainer = $('#tasksInfoContainer');
    const $infoCards = tasksInfoContainer.children();
    const $chatWindow = $('#chatWindow');
    const $openChatButton = $('#chatButton');
    const $closeChatButton = $('#closeChatButton');
    const $sessionCards = $('.session');
    const $sessionList = $('.sessionContainer');
    var $selectedCard = null

    if ($sessionCards.length > 0) {
        $selectedCard = $sessionCards.first() //Choosen button
    }
    let map; // Map variable
    let AdvancedMarkerElementOuter;

    const markers = []; // Container for storing markers


    let isInfoWindowOpen = false;

    // Initialize event handlers
    function setupEventHandlers() {
        // Toggle tasks info window visibility
        $infoArrow.on('click', onTasksInfoWindowClick);

        // Toggle chat
        $openChatButton.on('click', () => toggleChatWindow(true));
        $closeChatButton.on('click', () => toggleChatWindow(false));

        // Handle session clicks
        $sessionCards.on('click', onSessionCardClick);

        // Attach click event handler to complete buttons
        tasksInfoContainer.on('click', '.completeButton', onCompleteButtonClick);
    }

    // Toggle window info function
    function onTasksInfoWindowClick() {
        isInfoWindowOpen = !isInfoWindowOpen;

        if (isInfoWindowOpen) {
            $infoArrow.removeClass('up').addClass('down');
            $content.css('grid-template-rows', '3fr 1fr');
            $infoCards.css('display', 'flex');
            tasksInfoContainer.css('display', 'flex');
        } else {
            $infoArrow.removeClass('down').addClass('up');
            $content.css('grid-template-rows', '3fr 0.1fr');
            $infoCards.css('display', 'none');
            tasksInfoContainer.css('display', 'none');
        }
    }

    // Toggle chat window visibility
    function toggleChatWindow(show) {
        if (show) {
            $chatWindow.addClass('show');
            isChatWindowOpen = true;
            $openChatButton.hide();
        } else {
            $chatWindow.removeClass('show');
            isChatWindowOpen = false;
            setTimeout(() => $openChatButton.show(), 500);
        }
    }

    // Fetch new data from the server
    function fetchSessionTasksData(sessionId) {
        $.ajax({
            url: `/api/sessions/${sessionId}/tasks`,
            method: 'GET',
            success: updateTasksInfoWindow,
            error: (error) => console.error('Error fetching data:', error)
        });
    }

    function clearAllMarkers() {
        markers.forEach(marker => marker.setMap(null)); // Удаляем маркер с карты
        markers.length = 0; // Очищаем массив маркеров
    }


    // Handle session card click
    function onSessionCardClick() {
        if ($selectedCard != $(this)) {
            clearAllMarkers()
            $selectedCard = $(this);
            $sessionCards.removeClass('active');
            $selectedCard.addClass('active');

            const sessionId = $selectedCard.data('session-id');
            fetchSessionTasksData(sessionId);
            // fetchSessionActiveUsers(sessionId)
        }
    }


    // Update tasks info container with new data
    function updateTasksInfoWindow(data) {
        const html = data.map(item => {
            const completeButton = item.status === 'IN_PROGRESS'
                ? '<button type="button" class="button completeButton">Complete task</button>'
                : '';

            return `
                <div class="taskInfoCard" data-task-id="${item.id}">
                    <p>${item.name}</p>
                    <p>${item.description}</p>
                    <p>${item.status}</p>
                    ${completeButton}
                </div>
            `;
        }).join('');

        tasksInfoContainer.html(html);
    }

    // Handle complete button click
    function onCompleteButtonClick() {
        const taskId = $(this).parent().data('task-id');
        const taskName = $(this).parent().children().first().text();
        const selectedCardUser = $('.session').filter('.active').find('p').first().text()

        if (!confirm(`Are you sure you want to complete the quest "${taskName}" for user "${selectedCardUser}"?`)) {
            return;
        }

        $.ajax({
            url: `/api/tasks/${taskId}/complete`,
            method: 'PATCH',
            success: function (response) {
                console.log('Task completed successfully:', response);
                alert('Task completed successfully')
                const sessionId = $sessionCards.filter('.active').data('session-id');
                fetchSessionTasksData(sessionId);
            },
            error: function (xhr, status, error) {
                console.error('Error completing task:', status, error);
                alert('Failed to complete task. Please try again.');
            }

        });
    }

    function drawUserMarkers(users, session) {
        users.forEach(user => {
            if (user.session_id === session) {
                const marker = new AdvancedMarkerElementOuter({
                    map,
                    position: { lat: user.latitude, lng: user.longitude }
                })
                markers.push(marker)
            }
        });
    }




    function fetchActiveUsers() {
        return $.ajax({
            url: '/api/active_users',
            method: 'GET'
        }).then(function (response) {
            if (response && response.active_users) {
                return response.active_users;
            }
        }
        )
    };

    // WebSocket active_user coordinates recivier
    socket.on('usersCoordinatesUpdated', function (users) {
        updateUserCoordinatesOnMap(user.user_id, user.longitude, user.latitude);

    });

    // WebSocket active_user coordinates recivier
    function fetchActiveUsers(session_id) {
        console.log(session_id)
        socket.emit('getSessionUsersCoordinates', { session_id: session_id });
    }

    // Update sessions list
    socket.on('sessionUpdateClient', function (session) {
        var newSessionDiv = $('<div></div>')
            .attr('data-session-id', session.id)
            .addClass('session')
            .html('<p>' + session.host_name + '</p>' +
                '<p>Progress ' + session.progress + '</p>');

        newSessionDiv.on('click', onSessionCardClick)
        $sessionList.append(newSessionDiv);
    });



    socket.on('SessionUpdated', function (session) {
        console.log(session)
    });

    socket.on('Alert', (data) => {
        alert(data.message);
    });




    async function initMap() {
        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

        AdvancedMarkerElementOuter = AdvancedMarkerElement

        map = new Map(document.getElementById("map"), {
            center: { lat: 52.41142, lng: 16.93577 },
            zoom: 8,
            mapId: "e5b423fa9b5775e"
        });
    }

    async function drawInitialUserMarkers() {
        const data = await initMap();
        drawUserMarkers(active_users, $selectedCard.data('session-id'))
    }

    // Initialize the app
    function initApp() {
        setupEventHandlers();
        if ($selectedCard !== null) {
            $selectedCard.trigger('click');
        }
    }

    initApp();
    initMap();

    fetchActiveUsers().then(function (data) {
        active_users = data;
        drawInitialUserMarkers()
    });
});
