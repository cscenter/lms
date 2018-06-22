import React from 'react';
import PropTypes from 'prop-types';


class Pagination extends React.Component {
    static defaultProps = {
        showPrevious: false,
        showNext: false,
        currentPage: 1,
        pageSize: 10
    };

    constructor(props) {
        super(props);
        this.state = {pager: {}};
    }

    componentDidMount() {
        this.setPage(this.props.currentPage);
    };

    componentDidUpdate(prevProps, prevState) {
        if (this.state.pager.currentPage !== prevState.pager.currentPage) {
            // call change page function in parent component
            this.props.onChangePage(this.state.pager.currentPage);
        }
    }

    setPage(page) {
        let { pageSize } = this.props;
        let pager = this.state.pager;

        if (page < 1 || page > pager.totalPages) {
            return;
        }

        // get new pager object for specified page
        pager = this.getPager(this.props.totalItems, page, pageSize);

        if (pager.currentPage > pager.totalPages) {
            pager.currentPage = pager.totalPages;
        }

        // update state
        this.setState({ pager: pager });
    }

    getPager(totalItems, currentPage, pageSize) {
        // default to first page
        currentPage = currentPage || 1;

        // default page size is 10
        pageSize = pageSize || 10;

        // calculate total pages
        let totalPages = Math.ceil(totalItems / pageSize);

        let startPage, endPage;
        if (totalPages <= 10) {
            // less than 10 total pages so show all
            startPage = 1;
            endPage = totalPages;
        } else {
            if (currentPage + 4 >= totalPages) {
                startPage = totalPages - 9;
                endPage = totalPages;
            } else {
                startPage = currentPage - 5;
                endPage = currentPage + 4;
            }
        }

        // create an array of pages to ng-repeat in the pager control
        let pages = [...Array((endPage + 1) - startPage).keys()].map(i => startPage + i);

        // return object with all pager properties required by the view
        return {
            totalItems: totalItems,
            currentPage: currentPage,
            pageSize: pageSize,
            totalPages: totalPages,
            startPage: startPage,
            endPage: endPage,
            pages: pages
        };
    }

    render() {
        let pager = this.state.pager;
        // FIXME: move to willmount?
        if (!pager.pages || pager.pages.length <= 1) {
            // don't display pager if there is only 1 page
            return null;
        }

        return (
            <ul className="pagination">
                {
                    pager.currentPage !== 1 ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(1)}>В начало</button>
                        </li>
                    : ''
                }
                {
                    this.props.showPrevious ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(pager.currentPage - 1)}>Previous</button>
                        </li>
                    : ''
                }
                {
                    pager.pages.map((page, index) =>
                        <li key={index} className={`page-item ${pager.currentPage === page ? 'active' : ''}`}>
                            <button className="page-link" onClick={() => this.setPage(page)}>{page}</button>
                        </li>
                    )
                }
                {
                    this.props.showNext ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(pager.currentPage + 1)}>Next</button>
                        </li>
                    : ''
                }
                {
                    pager.currentPage !== pager.totalPages ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(pager.totalPages)}>В конец</button>
                        </li>
                    : ''
                }

            </ul>
        );
    }
}

Pagination.propTypes = {
    onChangePage: PropTypes.func.isRequired,
    pageSize: PropTypes.number,
    totalItems: PropTypes.number,
    currentPage: PropTypes.number,
};

export default Pagination;
