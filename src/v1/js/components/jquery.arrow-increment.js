/**
 * Copyright (c) 2012 Brian Stone
 */
(function ($) {

    /**
     * @param {node} element The HTML element.
     * @param {number} [opts.delta] Increment/decrement by the value of delta.
     * @param {number} [opts.min] The minimum value allowed.
     * @param {number} [otps.max] The maxiumum value allowed.
     * @param {function} [opts.parseFn] A custom parse function.
     * @param {function} [opts.formatFn] A custom format function.
     */
    $.arrowIncrement = function (element, opts) {
        var that = this;
        this.opts = $.extend({}, opts);
        this.$element = $(element).keydown(function (e) {
            if (e.keyCode === 38) { // up
                that.increment();
            } else if (e.keyCode === 40) { // down
                that.decrement();
            }
        });
    };

    /**
     * @param {boolean} decrement Decrement the value instead.
     */
    $.arrowIncrement.prototype.increment = function (decrement) {
        var value = this.$element.val(),
            parsed,
            computed;

        // Parse the value
        if (this.opts.parseFn) {
            parsed = this.opts.parseFn(value);
        } else {
            parsed = $.arrowIncrement.parse(value);
        }

        if (isNaN(parsed)) {
            return;
        }

        computed = $.arrowIncrement.compute(parsed, decrement, this.opts);

        // Apply formatting function
        if (this.opts.formatFn) {
            computed = this.opts.formatFn(computed);
        }

        this.$element.val(computed).change();
    };

    $.arrowIncrement.prototype.decrement = function () {
        this.increment(true);
    };

    /**
     * @static
     * @param {number} value The value to increment.
     * @param {boolean} decrement Decrement the value instead.
     * @param {number} [opts.delta] Increment/decrement by the value of delta.
     * @param {number} [opts.min] The minimum value allowed.
     * @param {number} [otps.max] The maxiumum value allowed.
     * @return {number} The incremented value.
     */
    $.arrowIncrement.compute = function (value, decrement, opts) {
        var computed, decimals, delta = 1,
            hasMin = opts && typeof opts.min === 'number',
            hasMax = opts && typeof opts.max === 'number';

        // check for delta option
        if (opts && typeof opts.delta == 'number') {
            delta = opts.delta;
        }

        if (decrement) {
            // return if already less than the minimum
            if (hasMin && value < opts.min) {
                return value;
            }
            computed = value - delta;
        } else {
            // return if already more than the maximum
            if (hasMax && value > opts.max) {
                return value;
            }
            computed = value + delta;
        }

        // Correct floating point errors by rounding to the smallest decimal
        decimals = Math.max(
            $.arrowIncrement.decimals(value),
            $.arrowIncrement.decimals(delta)
        );
        computed = +computed.toFixed(decimals);

        // If max and min overlap, max takes precedence
        if (hasMin && computed < opts.min) {
            computed = opts.min;
        }
        if (hasMax && computed > opts.max) {
            computed = opts.max;
        }

        return computed;
    };

    /**
     * @static
     * @param {number} value How many decimals places for this value.
     * @return {number} The number of decimal places.
     */
    $.arrowIncrement.decimals = function (value) {
        var str = '' + value,
            index = str.indexOf('.');
        if (index >= 0) {
            return str.length - 1 - str.indexOf('.');
        } else {
            return 0;
        }
    };

    /**
     * @static
     * @param {string} value The input value.
     * @return {number} The input value as a number.
     */
    $.arrowIncrement.parse = function (value) {
        var parsed = value.match(/^(\D*?)(\d*(,\d{3})*(\.\d+)?)\D*$/);
        if (parsed && parsed[2]) {
            if (parsed[1] && parsed[1].indexOf('-') >= 0) {
                return -parsed[2].replace(',', '');
            } else {
                return +parsed[2].replace(',', '');
            }
        }
        return NaN;
    };

    // Add to jQuery
    $.fn.arrowIncrement = function (opts) {
        return this.each(function () {
            (new $.arrowIncrement(this, opts));
        });
    };

}(jQuery));