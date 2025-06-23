/**
 * JavaScript file for making API calls to backend endpoints
 */

/**
 * Function to make a GET request to a specific endpoint
 * @param {string} endpoint - The endpoint to make the GET request to
 * @returns {Promise} - The response data from the GET request
 */
async function getFromApi(endpoint) {
    try {
        const response = await fetch(endpoint);
        if (!response.ok) {
            throw new Error('Failed to fetch data');
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching data:', error);
        return null;
    }
}

/**
 * Function to make a POST request to a specific endpoint with data
 * @param {string} endpoint - The endpoint to make the POST request to
 * @param {object} data - The data to be sent in the POST request
 * @returns {Promise} - The response data from the POST request
 */
async function postToApi(endpoint, data) {
    try {
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });
        if (!response.ok) {
            throw new Error('Failed to post data');
        }
        const responseData = await response.json();
        return responseData;
    } catch (error) {
        console.error('Error posting data:', error);
        return null;
    }
}

// Exporting functions to be used in other parts of the application
export { getFromApi, postToApi };