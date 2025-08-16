/**
 * Interview Setup Component - Handles interview configuration
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('interviewSetupComponent', {
            templateUrl: 'components/interview-setup/interview-setup.template.html',
            controller: 'InterviewSetupController',
            controllerAs: 'vm'
        });
})();