/**
 * Progress Component - AngularJS Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('progressComponent', {
            templateUrl: 'components/progress/progress.template.html',
            controller: 'ProgressController',
            controllerAs: 'vm'
        });
})();