// Frontend API service to make requests to the backend endpoints

/**
 * Function to make a GET request to a specified endpoint
 * @param {string} endpoint - The API endpoint to request data from
 * @returns {Promise} - A promise that resolves with the response data or rejects with an error
 */
async function getData(endpoint) {
    try {
        const response = await fetch(endpoint);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching data:', error);
        throw new Error('Failed to fetch data');
    }
}

/**
 * Function to make a POST request to a specified endpoint with data
 * @param {string} endpoint - The API endpoint to send data to
 * @param {object} data - The data to send in the request body
 * @returns {Promise} - A promise that resolves with the response data or rejects with an error
 */
async function postData(endpoint, data) {
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        const responseData = await response.json();
        return responseData;
    } catch (error) {
        console.error('Error posting data:', error);
        throw new Error('Failed to post data');
    }
}

// Export the functions to be used in other parts of the application
export { getData, postData };