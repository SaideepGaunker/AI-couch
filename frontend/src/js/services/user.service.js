/**
 * User Service for managing user profile and settings
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('UserService', UserService);

    UserService.$inject = ['$q', 'ApiService'];

    function UserService($q, ApiService) {
        var service = {
            getProfile: getProfile,
            updateProfile: updateProfile,
            changePassword: changePassword,
            getUserSettings: getUserSettings,
            updateUserSettings: updateUserSettings,
            exportUserData: exportUserData,
            deleteProfile: deleteProfile
        };

        return service;

        function getProfile() {
            return ApiService.get('/users/profile')
                .then(function(response) {
                    return response;
                });
        }

        function updateProfile(profileData) {
            return ApiService.put('/users/profile', profileData)
                .then(function(response) {
                    return response;
                });
        }

        function changePassword(passwordData) {
            return ApiService.post('/users/change-password', passwordData)
                .then(function(response) {
                    return response;
                });
        }

        function getUserSettings() {
            return ApiService.get('/users/settings')
                .then(function(response) {
                    return response;
                });
        }

        function updateUserSettings(settingsData) {
            return ApiService.put('/users/settings', settingsData)
                .then(function(response) {
                    return response;
                });
        }

        function exportUserData() {
            return ApiService.get('/users/export-data')
                .then(function(response) {
                    return response;
                });
        }

        function deleteProfile() {
            return ApiService.delete('/users/profile')
                .then(function(response) {
                    return response;
                });
        }
    }
})();