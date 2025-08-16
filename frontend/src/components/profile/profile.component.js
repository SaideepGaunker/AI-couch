/**
 * Profile Component - AngularJS Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('profileComponent', {
            templateUrl: 'components/profile/profile.template.html',
            controller: 'ProfileController',
            controllerAs: 'vm'
        });
})();