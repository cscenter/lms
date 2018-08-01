import React from 'react';
import PropTypes from 'prop-types';


class Pagination extends React.Component {
    static defaultProps = {
        showPrevious: false,
        showNext: false,
    };

    constructor(props) {
        super(props);
        const pager = Pagination.getPager(props.totalItems, props.currentPage, props.pageSize);
        this.state = { ...pager };
    }

    shouldComponentUpdate(nextProps, nextState) {
        return this.props.currentPage !== nextProps.currentPage;
    }

    setPage(page) {
        let pager = this.state;

        if (page < 1 || page > pager.totalPages) {
            return;
        }

        if (page !== this.props.currentPage) {
            this.props.onChangePage(page);
        }
    }

    static getPager(totalItems, currentPage, pageSize) {
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
            if (currentPage <= 6) {
                startPage = 1;
                endPage = 10;
            } else if (currentPage + 4 >= totalPages) {
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
            // currentPage: currentPage,
            pageSize: pageSize,
            totalPages: totalPages,
            startPage: startPage,
            endPage: endPage,
            pages: pages
        };
    }

    render() {
        let pager = this.state;
        let currentPage = this.props.currentPage;
        if (currentPage > pager.totalPages) {
            currentPage = pager.totalPages;
        }
        // FIXME: move to willmount?
        if (!pager.pages || pager.pages.length <= 1) {
            // don't display pager if there is only 1 page
            return null;
        }
        console.log("start pagination rendering", this.state);

        return (
            <ul className="pagination">
                {
                    currentPage !== 1 ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(1)}>В&nbsp;начало</button>
                        </li>
                    : ''
                }
                {
                    this.props.showPrevious ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(currentPage - 1)}>Previous</button>
                        </li>
                    : ''
                }
                {
                    pager.pages.map((page, index) =>
                        <li key={index} className={`page-item ${currentPage === page ? 'active' : ''}`}>
                            <button className="page-link" onClick={() => this.setPage(page)}>{page}</button>
                        </li>
                    )
                }
                {
                    this.props.showNext ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(currentPage + 1)}>Next</button>
                        </li>
                    : ''
                }
                {
                    currentPage !== pager.totalPages ?
                        <li className="page-item">
                            <button className="page-link" onClick={() => this.setPage(pager.totalPages)}>В&nbsp;конец</button>
                        </li>
                    : ''
                }

            </ul>
        );
    }
}

Pagination.propTypes = {
    onChangePage: PropTypes.func.isRequired,
    currentPage: PropTypes.number,
    pageSize: PropTypes.number,
    totalItems: PropTypes.number,
};

export default Pagination;
