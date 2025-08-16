/**
 * Login Component - AngularJS Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('loginComponent', {
            templateUrl: 'components/auth/login/login.template.html',
            controller: 'LoginController',
            controllerAs: 'vm'
        });
})();