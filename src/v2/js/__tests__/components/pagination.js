import * as React from 'react';
import { shallow } from 'enzyme';

import Pagination from 'components/Pagination';


let render = function(props) {
  return shallow(<Pagination {...props} />);
};

let props = {
    totalItems: 120,
    pageSize: 10,
    currentPage: 1,
    onChangePage: jest.fn(),
    marginPagesDisplayed: 1,
    pageRangeDisplayed: 3,
};

test('should render prev button as disabled if current page is 1', function() {
  let renderedComponent = render({...props, currentPage: 1});
  let button = renderedComponent.find('.page-item').at(0);
  expect(button.hasClass('disabled')).toEqual(true);
});

test('should render prev button as active if current page is 2', function() {
    let renderedComponent = render({...props, currentPage: 2});
  let nextButton = renderedComponent.find('.page-item').at(0);
  expect(nextButton.hasClass('disabled')).toEqual(false);
});

test('current page has class `active`', function() {
  let renderedComponent = render({...props, currentPage: 1});
  let button = renderedComponent.find('.page-item').at(1);
  expect(button.hasClass('active')).toEqual(true);
});

test('shows ellipsis after visible page range', function() {
  let renderedComponent = render({...props, currentPage: 1});
  let button = renderedComponent.find('.page-item').at(4);
  expect(button.hasClass('disabled')).toEqual(true);
  let renderExpectedHtmlEntity = shallow(<div>&hellip;</div>);
  expect(button.childAt(0).text()).toEqual(renderExpectedHtmlEntity.text());
});

test('shows ellipsis after visible page range, current page is 2', function() {
  let renderedComponent = render({...props, currentPage: 2});
  let button = renderedComponent.find('.page-item').at(4);
  expect(button.hasClass('disabled')).toEqual(true);
  let renderExpectedHtmlEntity = shallow(<div>&hellip;</div>);
  expect(button.childAt(0).text()).toEqual(renderExpectedHtmlEntity.text());
  button = renderedComponent.find('.page-item').at(2);
  expect(button.childAt(0).text()).toEqual("2");
});

test('fill small gap with button instead of ellipsis, check left side', function() {
  let renderExpectedHtmlEntity = shallow(<div>&hellip;</div>);
  let renderedComponent = render({...props, currentPage: 4});
  expect(renderedComponent.children()).toHaveLength(10);
  let button = renderedComponent.find('.page-item').at(5);
  expect(button.childAt(0).text()).toEqual("5");
  button = renderedComponent.find('.page-item').at(6);
  expect(button.hasClass('disabled')).toEqual(true);
  expect(button.childAt(0).text()).toEqual(renderExpectedHtmlEntity.text());
  button = renderedComponent.find('.page-item').at(2);
  expect(button.childAt(0).text()).toEqual("2");
  button = renderedComponent.find('.page-item').at(3);
  expect(button.childAt(0).text()).toEqual("3");
  button = renderedComponent.find('.page-item').at(4);
  expect(button.hasClass('active')).toEqual(true);
});

test('fill small gap with button instead of ellipsis, check right side', function() {
  let renderExpectedHtmlEntity = shallow(<div>&hellip;</div>);
  let renderedComponent = render({...props, currentPage: 9});
  expect(renderedComponent.children()).toHaveLength(10);
  let button = renderedComponent.find('.page-item').at(3);
  expect(button.childAt(0).text()).toEqual("8");
  button = renderedComponent.find('.page-item').at(2);
  expect(button.hasClass('disabled')).toEqual(true);
  expect(button.childAt(0).text()).toEqual(renderExpectedHtmlEntity.text());
  button = renderedComponent.find('.page-item').at(6);
  expect(button.childAt(0).text()).toEqual("11");
  button = renderedComponent.find('.page-item').at(4);
  expect(button.hasClass('active')).toEqual(true);
});

test('shows ellipsis before and after page range, current page is 5', function() {
  let renderExpectedHtmlEntity = shallow(<div>&hellip;</div>);
  let renderedComponent = render({...props, currentPage: 5});
  expect(renderedComponent.children()).toHaveLength(10);
  let button = renderedComponent.find('.page-item').at(5);
  expect(button.childAt(0).text()).toEqual("6");
  button = renderedComponent.find('.page-item').at(6);
  expect(button.hasClass('disabled')).toEqual(true);
  expect(button.childAt(0).text()).toEqual(renderExpectedHtmlEntity.text());
  button = renderedComponent.find('.page-item').at(2);
  expect(button.childAt(0).text()).toEqual(renderExpectedHtmlEntity.text());
  button = renderedComponent.find('.page-item').at(3);
  expect(button.childAt(0).text()).toEqual("4");
});

test('should render next button as active if current page is 1', function() {
    let renderedComponent = render({...props, currentPage: 1});
  let nextButton = renderedComponent.find('.page-item').last();
  expect(nextButton.hasClass('disabled')).toEqual(false);
});

test('should render next button as disabled if current page is last', function() {
    let renderedComponent = render({...props, currentPage: 12});
  let nextButton = renderedComponent.find('.page-item').last();
  expect(nextButton.hasClass('disabled')).toEqual(true);
});



