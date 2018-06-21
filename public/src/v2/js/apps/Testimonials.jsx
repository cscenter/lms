import FontFaceObserver from 'fontfaceobserver';
import Masonry from 'masonry-layout';
import $ from 'jquery';
import React from 'react';
import _debounce from 'lodash-es/debounce';

import Pagination from 'components/Pagination';
import Testimonial from 'components/Testimonial';
import {MOBILE_VIEWPORT_MAX} from 'utils';


function launch() {
    if (window.screen.availWidth >= MOBILE_VIEWPORT_MAX) {
        initMasonryGrid();
    } else {
        hideBodyPreloader();
    }
}

function initMasonryGrid() {
    const font = new FontFaceObserver('Fira Sans', {
      style: 'normal',
      weight: 400,
    });
    // Make sure font has been loaded and testimonial content rendered with it
    font.load().then(function () {
        let grid = new Masonry(document.querySelector('#masonry-grid'), {
            itemSelector: '.grid-item',
            // use element for option
            columnWidth: '.grid-sizer',
            percentPosition: true,
            initLayout: false
        });
        grid.once('layoutComplete', function() {
            hideBodyPreloader();
        });
        grid.layout();
    });
}

function showBodyPreloader() {
    $(document.body).addClass("_fullscreen").addClass("_loading");
}

function hideBodyPreloader() {
    $(document.body).removeClass("_fullscreen").removeClass("_loading");
}


class App extends React.Component {
    constructor(props) {
        super(props);
        this.masonryGrid = React.createRef();
        this.state = {
            loading: true,
            items: [],
            ...props.init.state
        };
        // bind function in constructor instead of render (https://github.com/yannickcr/eslint-plugin-react/blob/master/docs/rules/jsx-no-bind.md)
        this.onChangePage = this.onChangePage.bind(this);
        this.fetch = _debounce(this.fetch, 300);
    }

    componentDidMount = () => {
        let grid = new Masonry(this.masonryGrid.current, {
            itemSelector: '.grid-item',
            // use element for option
            columnWidth: '.grid-sizer',
            percentPosition: true,
            // transitionDuration: 0,
            initLayout: false
        });
        grid.on('layoutComplete', function() {
            hideBodyPreloader();
        });
        // Pagination component controls fetch
        console.log("componentDidMount");
    };

    onChangePage(page) {
        this.setState({ loading: true, page: page });
    }

    componentDidUpdate = (prevProps, prevState) => {
        console.log("componentDidUpdate");
        if (prevState.items.length === 0 || prevState.page !== this.state.page) {
            const payload = this.getRequestPayload(this.state);
            this.fetch(payload);
        } else {
            let grid = Masonry.data(this.masonryGrid.current);
            grid.reloadItems();
            grid.layout();
        }
    };

    getRequestPayload(state) {
        console.log(this.state);
        let {page} = state;
        console.log(page);
        return { page };
    }

    fetch = (payload) => {
        console.log("fetch");
        this.serverRequest = $.ajax({
            type: "GET",
            url: this.props.entry_url,
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
        });
    };

    render() {
        console.log("render");
        console.log(this.state.page);
        if (this.state.loading) {
            showBodyPreloader();
        }
        return (
            <div>
                <h1>Выпускники о CS центре</h1>
                <div className="row" id="masonry-grid" ref={this.masonryGrid}>
                    {this.state.items.map(item =>
                        <div className="grid-item" key={item.id}>
                            <div className="card mb-2" >
                                <Testimonial {...item} />
                            </div>
                        </div>
                    )}
                    <div className="grid-sizer" />
                </div>
                <Pagination totalItems={this.props.total} currentPage={this.state.page} onChangePage={this.onChangePage} />
            </div>
        );
    }
}

export default App;