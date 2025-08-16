/**
 * Register Component - AngularJS Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('registerComponent', {
            templateUrl: 'components/auth/register/register.template.html',
            controller: 'RegisterController',
            controllerAs: 'vm'
        });
})();