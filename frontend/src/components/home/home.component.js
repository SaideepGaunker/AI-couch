/**
 * Home Component - AngularJS Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('homeComponent', {
            templateUrl: 'components/home/home.template.html',
            controller: 'HomeController',
            controllerAs: 'vm'
        });
})();