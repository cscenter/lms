// TODO: add translation support (error msg)

import FontFaceObserver from 'fontfaceobserver';
import { createBrowserHistory } from "history";
import Masonry from 'masonry-layout';
import $ from 'jquery';
import React from 'react';
import _throttle from 'lodash-es/debounce';

import Pagination from 'components/Pagination';
import TestimonialCard from 'components/TestimonialCard';
import {showErrorNotification, showBodyPreloader,
    hideBodyPreloader} from 'utils';
import { DESKTOP_VIEWPORT_MIN } from "utils/media";


const MASONRY_ENABLED = (window.screen.availWidth >= DESKTOP_VIEWPORT_MIN);

const history = createBrowserHistory();


class App extends React.Component {
    constructor(props) {
        super(props);
        this.masonryGrid = React.createRef();
        this.state = {
            loading: true,
            items: [],
            ...props.initialState
        };
        // bind function in constructor instead of render (https://github.com/yannickcr/eslint-plugin-react/blob/master/docs/rules/jsx-no-bind.md)
        this.onChangePage = this.onChangePage.bind(this);
        this.fetch = _throttle(this.fetch, 300);
    }

    componentDidMount = () => {
        if (MASONRY_ENABLED) {
            let grid = new Masonry(this.masonryGrid.current, {
                itemSelector: '.grid-item',
                // use element for option
                columnWidth: '.grid-sizer',
                percentPosition: true,
                transitionDuration: 0,
                initLayout: false
            });
            grid.on('layoutComplete', function() {
                console.debug("masonry event: layoutComplete");
                hideBodyPreloader();
            });
        }

        history.listen((location, action) => {
          let nextPage = this.props.initialState.page;
          if (location.state && location.state.page !== this.state.page) {
              nextPage = location.state.page;
          }
          this.setState({
              loading: true,
              page: nextPage
          });
        });
        // const font = new FontFaceObserver('Fira Sans', {
        //   style: 'normal',
        //   weight: 400,
        // });
        // // Make sure font has been loaded before testimonial card rendering
        // font.load().then(function () {
        //     grid.layout();
        // });

        // Pagination component controls fetch
        this.setState({ loading: true, page: this.state.page });
        console.debug("Testimonials: componentDidMount");
    };

    componentWillUnmount() {
        this.serverRequest.abort();
    };

    onChangePage(page) {
        console.debug("onChangePage");
        history.push({
            pathname: history.location.pathname,
            search: `?page=${page}`,
            state: {page}
        });
        this.setState({ loading: true, page: page });
    }

    componentDidUpdate(prevProps, prevState) {
        console.debug("Testimonials: componentDidUpdate");
        if (this.state.loading) {
            const payload = this.getRequestPayload(this.state);
            this.fetch(payload);
        } else {
            if (MASONRY_ENABLED) {
                let grid = Masonry.data(this.masonryGrid.current);
                grid.reloadItems();
                grid.layout();
            } else {
                hideBodyPreloader();
            }
        }
    };

    getRequestPayload(state) {
        let {page} = state;
        return { page, page_size: this.props.page_size };
    }

    fetch = (payload) => {
        this.serverRequest = $.ajax({
            type: "GET",
            url: this.props.endpoint,
            dataType: "json",
            data: payload
        }).done((data) => {
            let areas = data.areas;
            data.results.map((item) => {
                let userAreas = item.areas.map((code) => areas[code]);
                item.areas = userAreas.join(", ");
            });
            this.setState({
                loading: false,
                items: data.results,
            });
        }).fail(() => {
            showErrorNotification("Ошибка загрузки данных. Попробуйте перезагрузить страницу.");
        });
    };

    render() {
        if (this.state.loading) {
            showBodyPreloader();
        }
        return (
            <div>
                <h1>Выпускники о CS центре</h1>
                <div id="masonry-grid" ref={this.masonryGrid}>
                    {this.state.items.map(item =>
                        <div className="grid-item" key={item.id}>
                            <div className="card mb-2" >
                                <div className="card__content">
                                    <TestimonialCard {...item} />
                                </div>
                            </div>
                        </div>
                    )}
                    <div className="grid-sizer" />
                </div>
                <Pagination totalItems={this.props.total} pageSize={this.props.page_size}
                            currentPage={this.state.page} onChangePage={this.onChangePage} />
            </div>
        );
    }
}

export default App;