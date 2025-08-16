/**
 * Dashboard Component - AngularJS Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('dashboardComponent', {
            templateUrl: 'components/dashboard/dashboard.template.html',
            controller: 'DashboardController',
            controllerAs: 'vm'
        });
})();