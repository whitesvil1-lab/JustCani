-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Dec 26, 2025 at 02:40 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `db_kasir1`
--

-- --------------------------------------------------------

--
-- Table structure for table `google_users`
--

CREATE TABLE `google_users` (
  `id` int(2) NOT NULL,
  `email` varchar(100) NOT NULL,
  `verified` varchar(10) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `google_users`
--

INSERT INTO `google_users` (`id`, `email`, `verified`, `created_at`) VALUES
(1, 'nabilvictar@gmail.com', '', '2025-12-19 14:00:54'),
(2, 'whitesvil1@gmail.com', '', '2025-12-25 22:05:12');

-- --------------------------------------------------------

--
-- Table structure for table `produk_biasa`
--

CREATE TABLE `produk_biasa` (
  `no_SKU` int(11) NOT NULL,
  `Name_product` varchar(100) NOT NULL,
  `expired_date` date NOT NULL,
  `Price` int(11) NOT NULL,
  `stok` int(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `produk_biasa`
--

INSERT INTO `produk_biasa` (`no_SKU`, `Name_product`, `expired_date`, `Price`, `stok`) VALUES
(1, 'TEAJUS GULA BATU 1 RENCENG', '2026-11-26', 6000, 16),
(3, 'KAIN PEL ', '2029-02-02', 10000, 19),
(5, 'GOOD DAY FREEZE SASCHET', '2026-11-11', 2000, 7),
(7, 'Mie nyemek Jogja', '2030-08-07', 2800, 0),
(4, 'SUNLIGHT', '2028-12-02', 5000, 10);

-- --------------------------------------------------------

--
-- Table structure for table `produk_lelang`
--

CREATE TABLE `produk_lelang` (
  `no_SKU` int(10) NOT NULL,
  `Name_product` varchar(100) NOT NULL,
  `expired_date` datetime NOT NULL,
  `Price` int(10) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `produk_lelang`
--

INSERT INTO `produk_lelang` (`no_SKU`, `Name_product`, `expired_date`, `Price`) VALUES
(2, 'NABATI KEJU 200GR', '2026-12-28 00:00:00', 1000),
(4, 'SOSIS SONICE', '2027-10-10 00:00:00', 500),
(6, 'LELE 1KG', '2026-01-25 00:00:00', 12500);

-- --------------------------------------------------------

--
-- Table structure for table `transaction_history`
--

CREATE TABLE `transaction_history` (
  `id` int(11) NOT NULL,
  `transaction_id` varchar(20) NOT NULL,
  `transaction_date` datetime DEFAULT current_timestamp(),
  `user_id` int(11) NOT NULL,
  `username` varchar(100) NOT NULL,
  `total_amount` decimal(12,2) NOT NULL,
  `transaction_type` enum('biasa','lelang') NOT NULL,
  `payment_method` varchar(50) DEFAULT 'cash',
  `items_count` int(11) NOT NULL,
  `details` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`details`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `google_user_id` int(11) DEFAULT NULL,
  `username` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL DEFAULT '',
  `whatsapp` varchar(20) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('admin','kasir','staff','') NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `google_user_id`, `username`, `email`, `whatsapp`, `password_hash`, `role`, `created_at`) VALUES
(2, 1, 'nabil', 'nabilvictar@gmail.com', NULL, '$2b$12$v9jiNSVBY5iNG24CTjtkuOfWCtdD9nqzfvJoOvk75N.vmXrCFyBL6', 'admin', '2025-12-26 01:38:59'),
(3, 2, 'whitesvil', 'whitesvil@gmail.com', NULL, '$2b$12$iiEq3bPJOzjT.DZtlLMCveHU3cCr3a9lNJmlk5dNdZvLdU9z5nFmW', 'admin', '2025-12-26 01:38:59'),
(4, NULL, 'nabilvactars', 'nabilvactars@gmail.com', '088811119999', '$2b$12$CYjGtYPc6ub/yG.OD38cqudQUpeKAp8HBgQEcL7nK4G/Lw3e29vvO', 'kasir', '2025-12-26 04:16:24'),
(5, NULL, 'whitesvil2', 'whitesvil2@gmail.com', '088811119999', '$2b$12$To853XFxmHOkfsu5XJmAiuPuF7ZxYvQph5Etzvzhjj0bwMpwxMYTy', 'kasir', '2025-12-26 04:18:12');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `google_users`
--
ALTER TABLE `google_users`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `produk_lelang`
--
ALTER TABLE `produk_lelang`
  ADD PRIMARY KEY (`no_SKU`);

--
-- Indexes for table `transaction_history`
--
ALTER TABLE `transaction_history`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `transaction_id` (`transaction_id`),
  ADD KEY `idx_user_id` (`user_id`),
  ADD KEY `idx_transaction_type` (`transaction_type`),
  ADD KEY `idx_transaction_date` (`transaction_date`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email_unique` (`email`),
  ADD UNIQUE KEY `google_user_id` (`google_user_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `google_users`
--
ALTER TABLE `google_users`
  MODIFY `id` int(2) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `produk_lelang`
--
ALTER TABLE `produk_lelang`
  MODIFY `no_SKU` int(10) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `transaction_history`
--
ALTER TABLE `transaction_history`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=6;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `transaction_history`
--
ALTER TABLE `transaction_history`
  ADD CONSTRAINT `fk_transaction_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `transaction_history_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
