import React from 'react';
import { render } from 'react-dom';
import configureStore from './store/configureStore.dev';
import Root from './containers/Root.dev';

const store = configureStore();

render(
  <Root store={store} />,
  document.getElementById('root')
);