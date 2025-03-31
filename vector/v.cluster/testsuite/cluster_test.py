import os
import tempfile
from grass.gunittest.case import TestCase
from grass.gunittest.main import test
from grass.script import core as grass
from grass.script import vector as gvector
from grass.script import vector_info


class TestVCluster(TestCase):
    @classmethod
    def setUpClass(cls):
        """Create test data with proper attribute table setup"""
        # Generate random points
        cls.runModule(
            "v.random", output="test_points", npoints=100, seed=42, overwrite=True
        )

    def setUp(self):
        self.temp_files = []
        self.temp_points = self.create_temp_file(
            "1 1\n1 2\n2 1\n2 2\n3 3\n11 11\n11 12\n12 11\n12 12\n50 50\n50 51\n51 50\n51 51\n100 100"
        )

        self.runModule(
            "v.in.ascii",
            input=self.temp_points,
            format="point",
            separator="space",
            output="test_points",
            overwrite=True,
        )

    def tearDown(self):
        """Removes all temporary files created during the tests."""
        for temp_file in self.temp_files:
            os.remove(temp_file)

    def create_temp_file(self, content):
        """Creates a temporary file with the given content and returns its path."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as temp_file:
            temp_file.write(content)
            temp_file_name = temp_file.name
        self.temp_files.append(temp_file_name)
        return temp_file_name

    def get_cluster_info(self, map_name):
        # Export the clustered points to ASCII format
        ascii_output = grass.read_command(
            "v.out.ascii", layer=2, input=map_name, format="point", separator="comma"
        )

        #print(ascii_output)
        # Parse the ASCII output to extract cluster IDs
        clusters = {}

        for line in ascii_output.splitlines():
            if line.strip():  # Skip empty lines
                parts = line.split(",")
                if len(parts) >= 3:
                    x, y, cluster_id = float(parts[0]), float(parts[1]), int(parts[2])
                    if cluster_id != 0:  # Skip noise points
                        if cluster_id not in clusters:
                            clusters[cluster_id] = []
                        clusters[cluster_id].append((x, y))
        return clusters

    def get_noise_points(self, map_name):
        ascii_output = grass.read_command(
            "v.out.ascii", layer=2, input=map_name, format="point", separator="comma"
        )

        noise_points = []
        for line in ascii_output.splitlines():
            if line.strip():
                parts = line.split(",")
                if len(parts) >= 3:
                    cluster_id = int(parts[2])
                    if cluster_id == 0:
                        noise_points.append(cluster_id)

        return noise_points

    def test_cluster_formation(self):
        """Test DBSCAN clustering with proper attribute handling"""
        # Run clustering with clean table creation
        self.assertModule(
            "v.cluster",
            input="test_points",
            output="clustered",
            method="dbscan",
            distance=1.5,
            min=4,
            flags="b",  # Create new table
            overwrite=True,
        )

        info = vector_info("clustered")

        clusters = self.get_cluster_info("clustered")
        #print(clusters)
        self.assertGreater(len(clusters), 1)
        cluster_sizes = sorted([len(points) for _, points in clusters.items()])
        self.assertEqual(cluster_sizes, [4, 4, 5])

        noise_points = self.get_noise_points("clustered")
        self.assertEqual(len(noise_points), 1)

    def test_min_points(self):
        """Testing the effect of the min points parameter on clustering"""
        self.assertModule(
            "v.cluster",
            input="test_points",
            output="clustered",
            method="dbscan",
            distance=1.5,
            min=5,
            flags="b",
            overwrite=True,
        )

        clusters = self.get_cluster_info("clustered")
        self.assertEqual(len(clusters), 1)

    def test_distance_threshold_effect(self):
        """Test that distance threshold correctly affects cluster formation"""

        self.assertModule(
            "v.cluster",
            input="test_points",
            output="clustered",
            method="dbscan",
            distance=1.5,
            min=4,
            flags="b",
            overwrite=True,
        )

        clusters = self.get_cluster_info("clustered")
        nodes = len(clusters[1])
        #print(nodes)

        self.assertModule(
            "v.cluster",
            input="test_points",
            output="clustered_20",
            method="dbscan",
            distance=20,
            min=4,
            flags="b",
            overwrite=True,
        )

        # info = vector_info("clustered")
        clusters_20 = self.get_cluster_info("clustered_20")
        nodes_20 = len(clusters_20[1])

        self.assertGreaterEqual(nodes_20, nodes)

    @classmethod
    def tearDownClass(cls):
        """Clean up"""
        cls.runModule(
            "g.remove", type="vector", name="test_points,clustered", flags="f"
        )


if __name__ == "__main__":
    test()
