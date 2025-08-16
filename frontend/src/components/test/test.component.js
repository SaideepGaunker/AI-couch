/**
 * Test Component - Quick interview test
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('testComponent', {
            templateUrl: 'components/test/test.template.html',
            controller: 'TestController',
            controllerAs: 'vm'
        });
})();