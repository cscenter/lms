import * as React from 'react';
import { shallow } from 'enzyme';

import UserCard from 'components/UserCard';


let render = function(props) {
  return shallow(<UserCard {...props} />)
};

test('should render "Hello, World!" as title', function() {
  let renderedComponent = render({id: 42, name: "Gordon"});
  let header = renderedComponent.find('div.user-card__details');
  expect(header.text()).toBe("Gordon");
});

