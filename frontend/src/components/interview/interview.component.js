/**
 * Interview Component - AngularJS Component-based Architecture
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('interviewComponent', {
            templateUrl: 'components/interview/interview.template.html',
            controller: 'InterviewController',
            controllerAs: 'vm'
        });
})();