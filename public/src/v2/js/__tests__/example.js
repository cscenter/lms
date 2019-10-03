import * as React from 'react';
import { shallow } from 'enzyme';

import UserCard from 'components/UserCard';


let render = function(props) {
  return shallow(<UserCard {...props} />)
};

test('should render "Gordon" as card title', function() {
  let renderedComponent = render({id: 42, name: "Gordon", url: "/users/42/", photo: "/path/to/img/"});
  let header = renderedComponent.find('div.card__title');
  expect(header.text()).toBe("Gordon");
});

