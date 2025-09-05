/**
 * Session Data Service - Temporary storage for session data during navigation
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('SessionDataService', SessionDataService);

    SessionDataService.$inject = [];

    function SessionDataService() {
        var service = {
            setSessionData: setSessionData,
            getSessionData: getSessionData,
            clearSessionData: clearSessionData,
            validateSessionData: validateSessionData,
            hasValidSessionData: hasValidSessionData,
            getSessionState: getSessionState,
            setSessionState: setSessionState,
            clearSessionState: clearSessionState
        };

        return service;

        function setSessionData(sessionData) {
            try {
                // Validate session data before storing
                if (!validateSessionData(sessionData)) {
                    console.error('Invalid session data provided:', sessionData);
                    return false;
                }

                // Store session data temporarily in localStorage with timestamp
                var dataToStore = {
                    data: sessionData,
                    timestamp: Date.now(),
                    version: '1.0'
                };
                
                localStorage.setItem('temp_session_data', JSON.stringify(dataToStore));
                console.log('Session data stored successfully');
                return true;
            } catch (e) {
                console.error('Error storing session data:', e);
                return false;
            }
        }

        function getSessionData() {
            try {
                var storedData = localStorage.getItem('temp_session_data');
                if (!storedData) {
                    return null;
                }

                var parsedData = JSON.parse(storedData);
                
                // Check if data is expired (older than 1 hour)
                var oneHour = 60 * 60 * 1000;
                if (parsedData.timestamp && (Date.now() - parsedData.timestamp > oneHour)) {
                    console.warn('Session data expired, clearing...');
                    clearSessionData();
                    return null;
                }

                // Validate the retrieved data
                if (!validateSessionData(parsedData.data)) {
                    console.error('Retrieved session data is invalid, clearing...');
                    clearSessionData();
                    return null;
                }

                return parsedData.data;
            } catch (e) {
                console.error('Error retrieving session data:', e);
                clearSessionData(); // Clear corrupted data
                return null;
            }
        }

        function clearSessionData() {
            try {
                localStorage.removeItem('temp_session_data');
                console.log('Session data cleared');
            } catch (e) {
                console.error('Error clearing session data:', e);
            }
        }

        function validateSessionData(sessionData) {
            if (!sessionData) {
                return false;
            }

            // Check required fields
            if (!sessionData.session || !sessionData.session.id) {
                console.error('Session data missing session or session.id');
                return false;
            }

            if (!sessionData.questions || !Array.isArray(sessionData.questions)) {
                console.error('Session data missing questions array');
                return false;
            }

            if (sessionData.questions.length === 0) {
                console.error('Session data has empty questions array');
                return false;
            }

            return true;
        }

        function hasValidSessionData() {
            var data = getSessionData();
            return data !== null;
        }

        function getSessionState() {
            try {
                var stateData = localStorage.getItem('session_state');
                if (stateData) {
                    return JSON.parse(stateData);
                }
                return null;
            } catch (e) {
                console.error('Error retrieving session state:', e);
                return null;
            }
        }

        function setSessionState(sessionId, state) {
            try {
                var stateData = {
                    sessionId: sessionId,
                    state: state,
                    timestamp: Date.now()
                };
                localStorage.setItem('session_state', JSON.stringify(stateData));
                return true;
            } catch (e) {
                console.error('Error storing session state:', e);
                return false;
            }
        }

        function clearSessionState() {
            try {
                localStorage.removeItem('session_state');
            } catch (e) {
                console.error('Error clearing session state:', e);
            }
        }
    }
})();