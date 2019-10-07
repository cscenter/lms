const Enzyme = require('enzyme');
const EnzymeAdapter = require('enzyme-adapter-react-16');

// React 16 Enzyme adapter
Enzyme.configure({ adapter: new EnzymeAdapter() });

global.jQuery = global.$ = require('jquery');
