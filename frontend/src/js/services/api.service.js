/**
 * API Service for HTTP requests
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .service('ApiService', ApiService);

    ApiService.$inject = ['$http', '$q'];

    function ApiService($http, $q) {
        var service = {
            baseUrl: 'http://localhost:8000/api/v1',
            get: get,
            post: post,
            put: put,
            delete: deleteRequest
        };

        return service;

        function get(endpoint, params) {
            var config = {
                params: params || {},
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            return $http.get(service.baseUrl + endpoint, config)
                .then(handleSuccess)
                .catch(handleError);
        }

        function post(endpoint, data) {
            var config = {
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            return $http.post(service.baseUrl + endpoint, data, config)
                .then(handleSuccess)
                .catch(handleError);
        }

        function put(endpoint, data) {
            var config = {
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            return $http.put(service.baseUrl + endpoint, data, config)
                .then(handleSuccess)
                .catch(handleError);
        }

        function deleteRequest(endpoint) {
            var config = {
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            return $http.delete(service.baseUrl + endpoint, config)
                .then(handleSuccess)
                .catch(handleError);
        }

        function handleSuccess(response) {
            return response.data;
        }

        function handleError(error) {
            console.error('API Error:', error);
            return $q.reject(error);
        }
    }
})();