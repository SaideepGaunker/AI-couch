// Karma configuration for end-to-end testing
module.exports = function (config) {
    config.set({
        // Base path that will be used to resolve all patterns (eg. files, exclude)
        basePath: '',

        // Frameworks to use
        frameworks: ['jasmine'],

        // List of files / patterns to load in the browser
        files: [
            'node_modules/angular/angular.js',
            'node_modules/angular-route/angular-route.js',
            'node_modules/angular-animate/angular-animate.js',
            'node_modules/angular-sanitize/angular-sanitize.js',
            'node_modules/angular-mocks/angular-mocks.js',
            'src/js/app.js',
            'src/js/**/*.js',
            'src/components/**/*.js',
            'tests/**/*.spec.js'
        ],

        // List of files / patterns to exclude
        exclude: [],

        // Preprocess matching files before serving them to the browser
        preprocessors: {},

        // Test results reporter to use
        reporters: ['progress', 'kjhtml'],

        // Web server port
        port: 9876,

        // Enable / disable colors in the output (reporters and logs)
        colors: true,

        // Level of logging
        logLevel: config.LOG_INFO,

        // Enable / disable watching file and executing tests whenever any file changes
        autoWatch: true,

        // Start these browsers
        browsers: ['Chrome'],

        // Continuous Integration mode
        singleRun: false,

        // Concurrency level
        concurrency: Infinity
    });
};