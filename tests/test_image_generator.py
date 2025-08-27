import unittest
import os
from app.image_generator import create_instagram_post

class TestImageGenerator(unittest.TestCase):

    def test_create_instagram_post(self):
        """_summary_
        This function is used to test the create_instagram_post function
        """
        # Define a sample news text and image path for testing
        sample_news = "This is a test news headline."
        test_image_path = "test_instagram_post.png"

        # Call the function to create the image
        create_instagram_post(sample_news, test_image_path)

        # Check if the image file was created
        self.assertTrue(os.path.exists(test_image_path))

        # Clean up the created image file
        os.remove(test_image_path)

if __name__ == '__main__':
    unittest.main()
