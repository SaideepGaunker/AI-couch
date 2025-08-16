/**
 * Interview Chat Component - Chatbot-style interview with audio
 */
(function() {
    'use strict';

    angular
        .module('interviewPrepApp')
        .component('interviewChatComponent', {
            templateUrl: 'components/interview-chat/interview-chat.template.html',
            controller: 'InterviewChatController',
            controllerAs: 'vm'
        });
})();